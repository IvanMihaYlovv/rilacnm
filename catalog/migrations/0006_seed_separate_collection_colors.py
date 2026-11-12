from django.db import migrations

# The blue/green/yellow split is already in these products' specifications;
# the hex codes are display approximations for the swatches.
COLORS = (
    'Син | #1f5aa6 | хартиени отпадъци\n'
    'Зелен | #2e7d32 | отпадъци от стъкло\n'
    'Жълт | #f2c200 | пластмасови отпадъци'
)
SLUGS = ['konteyneri-za-razdelno-sabirane', 'metalna-kofa-za-razdelno-sabirane']


def seed(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    Product.objects.filter(slug__in=SLUGS, colors='').update(colors=COLORS)


def unseed(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    Product.objects.filter(slug__in=SLUGS, colors=COLORS).update(colors='')


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0005_product_colors_drawing'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
