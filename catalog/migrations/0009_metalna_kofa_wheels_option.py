from django.db import migrations

SLUG = 'metalna-kofa'
OPTIONS = 'Без колела\nС колела'
# Photo file name (without folder) -> variant it shows.
PHOTO_VARIANTS = {'zatvorena.jpg': 'Без колела', 's-kolela.jpg': 'С колела'}


def seed(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    ProductImage = apps.get_model('catalog', 'ProductImage')
    Product.objects.filter(slug=SLUG, colors='').update(colors=OPTIONS)
    for image in ProductImage.objects.filter(product__slug=SLUG, color=''):
        variant = PHOTO_VARIANTS.get(image.image.name.rsplit('/', 1)[-1])
        if variant:
            image.color = variant
            image.save(update_fields=['color'])


def unseed(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    ProductImage = apps.get_model('catalog', 'ProductImage')
    Product.objects.filter(slug=SLUG, colors=OPTIONS).update(colors='')
    ProductImage.objects.filter(product__slug=SLUG, color__in=PHOTO_VARIANTS.values()).update(color='')


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0008_household_container_colors'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
