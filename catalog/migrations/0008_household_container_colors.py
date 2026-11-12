from django.db import migrations

SLUG = 'stomanen-konteyner-bitov'
# Hex codes are sampled from the product photos, slightly deepened.
COLORS = 'Сив | #9a9c9a\nЧервен | #d32f2f\nЧерен | #2b2c2b'
# Photo file name (without folder) -> colour it shows.
PHOTO_COLORS = {'siv.jpg': 'Сив', 'cherven.jpg': 'Червен', 'cheren.jpg': 'Черен'}


def seed(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    ProductImage = apps.get_model('catalog', 'ProductImage')
    Product.objects.filter(slug=SLUG, colors='').update(colors=COLORS)
    for image in ProductImage.objects.filter(product__slug=SLUG, color=''):
        color = PHOTO_COLORS.get(image.image.name.rsplit('/', 1)[-1])
        if color:
            image.color = color
            image.save(update_fields=['color'])


def unseed(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    ProductImage = apps.get_model('catalog', 'ProductImage')
    Product.objects.filter(slug=SLUG, colors=COLORS).update(colors='')
    ProductImage.objects.filter(product__slug=SLUG, color__in=PHOTO_COLORS.values()).update(color='')


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0007_productimage_color'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
