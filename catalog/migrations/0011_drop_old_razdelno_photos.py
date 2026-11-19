from django.core.files.storage import default_storage
from django.db import migrations

SLUG = 'konteyneri-za-razdelno-sabirane'
OLD_PHOTOS = ['tri-tsvyata.jpg', 'sin.jpg', 'sini-seriya.jpg', 'zelen-zhalt-sin.jpg']


def drop(apps, schema_editor):
    ProductImage = apps.get_model('catalog', 'ProductImage')
    images = ProductImage.objects.filter(product__slug=SLUG)
    for image in images:
        if image.image.name.rsplit('/', 1)[-1] in OLD_PHOTOS:
            name = image.image.name
            image.delete()
            if default_storage.exists(name):
                default_storage.delete(name)
    # The primary photo may have been among them: promote the first one left.
    remaining = list(ProductImage.objects.filter(product__slug=SLUG).order_by('order', 'pk'))
    if remaining and not any(i.is_primary for i in remaining):
        remaining[0].is_primary = True
    for order, image in enumerate(remaining):
        image.order = order
        image.save(update_fields=['is_primary', 'order'])


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0010_merge_metalna_kofa_razdelno'),
    ]

    operations = [
        migrations.RunPython(drop, migrations.RunPython.noop),
    ]
