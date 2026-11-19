from django.core.files.storage import default_storage
from django.db import migrations

OLD_SLUG = 'metalna-kofa-za-razdelno-sabirane'
NEW_SLUG = 'konteyneri-za-razdelno-sabirane'


def merge(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    ProductImage = apps.get_model('catalog', 'ProductImage')
    old = Product.objects.filter(slug=OLD_SLUG).first()
    new = Product.objects.filter(slug=NEW_SLUG).first()
    if old is None:
        return
    if new is not None:
        # Append after the photos the target already has.
        next_order = max((i.order for i in ProductImage.objects.filter(product=new)), default=-1) + 1
        for image in ProductImage.objects.filter(product=old).order_by('order', 'pk'):
            old_name = image.image.name
            new_name = old_name.replace(f'products/{OLD_SLUG}/', f'products/{NEW_SLUG}/', 1)
            if old_name != new_name and default_storage.exists(old_name) and not default_storage.exists(new_name):
                with default_storage.open(old_name) as src:
                    default_storage.save(new_name, src)
                default_storage.delete(old_name)
            image.image.name = new_name
            image.product = new
            image.is_primary = False
            image.order = next_order
            next_order += 1
            image.save()
    old.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0009_metalna_kofa_wheels_option'),
    ]

    operations = [
        migrations.RunPython(merge, migrations.RunPython.noop),
    ]
