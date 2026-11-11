import os

from django import forms
from django.conf import settings
from django.template.defaultfilters import filesizeformat

from catalog.models import Product

from .models import ContactMessage, Inquiry


class SubmissionForm(forms.ModelForm):
    # Honeypot: hidden from people via CSS, bots tend to fill it in.
    website = forms.CharField(required=False, label='Уебсайт',
                              widget=forms.TextInput(attrs={'tabindex': '-1', 'autocomplete': 'off'}))

    autocomplete = {'name': 'name', 'email': 'email', 'phone': 'tel', 'company': 'organization'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault('placeholder', ' ')
            if name in self.autocomplete:
                field.widget.attrs['autocomplete'] = self.autocomplete[name]
        self.fields['phone'].widget.input_type = 'tel'
        self.fields['message'].widget.attrs['rows'] = 4

    def is_spam(self):
        return bool(self.cleaned_data.get('website'))


# Drawings (CAD and PDF), photos, office documents and archives. Never HTML, SVG or anything
# a browser would run: staff only download the files, but this keeps them harmless.
ATTACHMENT_EXTENSIONS = (
    '.pdf', '.dwg', '.dxf', '.dwf', '.step', '.stp', '.iges', '.igs', '.stl',
    '.jpg', '.jpeg', '.png', '.webp', '.heic',
    '.doc', '.docx', '.xls', '.xlsx', '.odt', '.ods', '.txt',
    '.zip', '.rar', '.7z',
)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Several files in one input; cleans to a list (empty when nothing was chosen)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        files = data if isinstance(data, (list, tuple)) else [data]
        return [super(MultipleFileField, self).clean(f, initial) for f in files if f]

    def validate(self, value):
        # One file at a time comes through FileField.clean(); the list is checked by the form.
        pass


class InquiryForm(SubmissionForm):
    prefix = 'inq'

    attachments = MultipleFileField(
        label='Чертежи, скици или снимки', required=False,
        help_text=(f'По желание · до {settings.INQUIRY_MAX_FILES} файла, '
                   f'до {settings.INQUIRY_MAX_FILE_MB} MB всеки'),
    )
    attachment_types = 'PDF, DWG, DXF, STEP, JPG, PNG, ZIP и др.'

    class Meta:
        model = Inquiry
        fields = ['name', 'company', 'email', 'phone', 'product', 'quantity', 'message']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.active().select_related('category')
        self.fields['product'].empty_label = 'Не съм сигурен / по проект'
        self.fields['quantity'].widget.attrs['min'] = 1
        self.fields['attachments'].widget.attrs['accept'] = ','.join(ATTACHMENT_EXTENSIONS)

    def clean_attachments(self):
        files = self.cleaned_data['attachments']
        if len(files) > settings.INQUIRY_MAX_FILES:
            raise forms.ValidationError(f'Може да прикачите най-много {settings.INQUIRY_MAX_FILES} файла.')
        for f in files:
            if os.path.splitext(f.name)[1].lower() not in ATTACHMENT_EXTENSIONS:
                raise forms.ValidationError(f'„{f.name}“: този вид файл не се приема.')
            if f.size > settings.INQUIRY_MAX_FILE_MB * 1024 * 1024:
                raise forms.ValidationError(
                    f'„{f.name}“ е {filesizeformat(f.size)}: максимумът е {settings.INQUIRY_MAX_FILE_MB} MB.')
        if sum(f.size for f in files) > settings.INQUIRY_MAX_TOTAL_MB * 1024 * 1024:
            raise forms.ValidationError(f'Общият размер е над {settings.INQUIRY_MAX_TOTAL_MB} MB.')
        return files

    def save_attachments(self, inquiry):
        from .models import InquiryAttachment
        for f in self.cleaned_data.get('attachments', []):
            InquiryAttachment.objects.create(inquiry=inquiry, file=f, original_name=f.name[:255], size=f.size)


class ContactMessageForm(SubmissionForm):
    prefix = 'msg'

    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']
