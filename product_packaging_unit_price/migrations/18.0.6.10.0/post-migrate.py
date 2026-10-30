# -*- coding: utf-8 -*-


def migrate(cr, version):
    """ Colis par palette des conditionnements existants, une seule fois :
    100 pour les caisses plastique, 220 pour les autres (règle utilisée jusqu'ici sur la facture). """
    cr.execute("""
        UPDATE product_packaging
           SET pallet_packaging_qty = CASE WHEN UPPER(name) LIKE '%PLASTIQUE%' THEN 100 ELSE 220 END
         WHERE COALESCE(pallet_packaging_qty, 0) = 0
    """)
