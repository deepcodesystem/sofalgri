# -*- coding: utf-8 -*-
""" Calculs communs aux documents d'export (facture transitaire, facture pro forma) :
lignes regroupées par produit et nombre de palettes. Les lignes passées sont des lignes
de facture ou de commande ; les noms des champs quantité / unité sont donnés en paramètre. """
import math


def packaging_label(packaging):
    return packaging.description_sale or packaging.name or ''


def colis_per_pallet(packaging):
    """ Colis par palette du conditionnement ; à défaut, ancienne règle : 100 pour les caisses
    plastique, 220 pour les autres. """
    if packaging.pallet_packaging_qty:
        return packaging.pallet_packaging_qty
    return 100 if 'PLASTIQUE' in (packaging.name or '').upper() else 220


def group_export_lines(lines, qty_field, uom_field):
    """ Une ligne par désignation (ex. « AVOCAT HASS ») : plage de calibres, colis,
    types d'emballage, poids net, montant et prix unitaire moyen (montant / poids). """
    groups = {}
    for line in lines:
        product = line.product_id
        designation = product.description_sale or product.product_tmpl_id.name or line.name or ''
        variety = 'product_variety' in product._fields and product.product_variety
        if variety and variety.upper() not in designation.upper():
            designation = f"{designation} {variety}"
        group = groups.setdefault(designation, {
            'designation': designation,
            'calibres': [],
            'packaging_qty': 0.0,
            'packagings': [],
            'quantity': 0.0,
            'uom': line[uom_field].name,
            'amount': 0.0,
        })
        calibre = 'calibre' in product._fields and product.calibre
        if calibre and calibre not in group['calibres']:
            group['calibres'].append(calibre)
        label = packaging_label(line.product_packaging_id)
        if label and label not in group['packagings']:
            group['packagings'].append(label)
        group['packaging_qty'] += line.product_packaging_qty
        group['quantity'] += line[qty_field]
        group['amount'] += line.price_subtotal

    for group in groups.values():
        calibres = group['calibres']
        numbers = sorted(int(c) for c in calibres if c.strip().isdigit())
        if numbers and len(numbers) == len(calibres):
            group['calibre'] = f"CAL {numbers[0]}" if numbers[0] == numbers[-1] else f"CAL {numbers[0]}-{numbers[-1]}"
        else:
            group['calibre'] = ', '.join(calibres)
        group['packaging'] = ' & '.join(group['packagings'])
        group['unit_price'] = group['amount'] / group['quantity'] if group['quantity'] else 0.0
    return list(groups.values())


def shipping_summary(lines, qty_field, gross_weight):
    """ Colis, palettes et poids. Palettes : colis regroupés par nombre de colis par palette
    du conditionnement, chaque groupe arrondi à la palette supérieure ; poids brut saisi. """
    packages_by_pallet_size = {}
    for line in lines:
        size = colis_per_pallet(line.product_packaging_id)
        packages_by_pallet_size[size] = packages_by_pallet_size.get(size, 0.0) + line.product_packaging_qty
    pallets = sum(math.ceil(packages / size) for size, packages in packages_by_pallet_size.items() if packages > 0)
    return {
        'packages': sum(lines.mapped('product_packaging_qty')),
        'pallets': pallets,
        'net_weight': sum(lines.mapped(qty_field)),
        'gross_weight': gross_weight,
    }
