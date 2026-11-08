# -*- coding: utf-8 -*-


def migrate(cr, version):
    """ Transitaire et station sur les factures d'export de la saison déjà créées : les champs calculés
    à la mise à jour le sont avant le chargement des tarifs, donc à 0. """
    cr.execute("""
        WITH tariffs AS (
            SELECT (SELECT amount FROM sofalgri_export_tariff
                     WHERE cost_type = 'forwarder' AND active ORDER BY sequence, name, id LIMIT 1) AS forwarder,
                   (SELECT amount FROM sofalgri_export_tariff
                     WHERE cost_type = 'station' AND active ORDER BY sequence, name, id LIMIT 1) AS station
        ),
        weights AS (
            SELECT line.move_id, SUM(line.quantity) AS kg
              FROM account_move_line line
              JOIN product_product product ON product.id = line.product_id
              JOIN product_template template ON template.id = product.product_tmpl_id
             WHERE line.display_type = 'product' AND template.is_storable
             GROUP BY line.move_id
        )
        UPDATE account_move move
           SET export_forwarder_cost = COALESCE(tariffs.forwarder, 0),
               export_station_cost = ROUND((COALESCE(weights.kg, 0) * COALESCE(tariffs.station, 0))::numeric, 2)
          FROM tariffs, account_fiscal_position fiscal_position, res_company company, weights
         WHERE weights.move_id = move.id
           AND fiscal_position.id = move.fiscal_position_id
           AND company.id = move.company_id
           AND move.move_type = 'out_invoice'
           AND move.state <> 'cancel'
           AND fiscal_position.name::text ILIKE '%Export%'
           AND (company.season_start_date IS NULL
                OR COALESCE(move.invoice_date, move.date) >= company.season_start_date)
    """)
