from django import forms

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


class InquiryForm(SubmissionForm):
    prefix = 'inq'

    class Meta:
        model = Inquiry
        fields = ['name', 'company', 'email', 'phone', 'product', 'quantity', 'message']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.active().select_related('category')
        self.fields['product'].empty_label = 'Не съм сигурен / по проект'
        self.fields['quantity'].widget.attrs['min'] = 1


class ContactMessageForm(SubmissionForm):
    prefix = 'msg'

    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']
