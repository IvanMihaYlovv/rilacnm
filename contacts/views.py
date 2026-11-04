from django.contrib import messages
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from core.seo import SeoPageMixin

from .forms import ContactMessageForm, InquiryForm

THROTTLE_LIMIT = 5
THROTTLE_WINDOW = 60 * 10  # seconds


def _client_ip(request):
    # Behind a reverse proxy, configure it to set REMOTE_ADDR correctly
    # rather than trusting a client-supplied X-Forwarded-For here.
    return request.META.get('REMOTE_ADDR')


def _throttled(ip):
    key = f'contacts:throttle:{ip}'
    cache.add(key, 0, THROTTLE_WINDOW)
    try:
        return cache.incr(key) > THROTTLE_LIMIT
    except ValueError:  # key expired between add() and incr()
        cache.set(key, 1, THROTTLE_WINDOW)
        return False


def _wants_json(request):
    return 'application/json' in request.headers.get('Accept', '')


def _back_url(request):
    """Where to send no-JS visitors after submitting: the page the form was on."""
    next_url = request.POST.get('next', '')
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()},
                                       require_https=request.is_secure()):
        return next_url
    return reverse('contacts:page') + '#formulyar'


def _handle(request, form_class, success_message):
    form = form_class(request.POST)
    ip = _client_ip(request)
    back = _back_url(request)

    if _throttled(ip):
        error = 'Получихме много съобщения от вас. Опитайте отново след няколко минути.'
        if _wants_json(request):
            return JsonResponse({'ok': False, 'message': error}, status=429)
        messages.error(request, error)
        return redirect(back)

    if not form.is_valid():
        if _wants_json(request):
            return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
        messages.error(request, 'Моля, проверете попълнените полета.')
        return redirect(back)

    # Pretend success for bots so they don't learn to adapt.
    if not form.is_spam():
        submission = form.save(commit=False)
        submission.ip_address = ip
        submission.user_agent = request.headers.get('User-Agent', '')[:300]
        submission.save()

    if _wants_json(request):
        return JsonResponse({'ok': True, 'message': success_message})
    messages.success(request, success_message)
    return redirect(back)


class ContactPageView(SeoPageMixin, TemplateView):
    template_name = 'contacts/contact.html'
    page_type = 'ContactPage'
    page_title = 'Контакти — адрес, телефони и запитване за оферта'
    page_heading = 'Разкажете ни какво ви трябва'
    page_lead = 'Отговаряме с оферта обикновено до един работен ден. Ако бързате — просто ни звъннете.'
    page_eyebrow = 'Контакти'
    page_description = ('РИЛА-СНМ ЕООД, гр. Рила, ул. „Цар Симеон“ № 1. Тел. +359 7054 2024, '
                        'cnm_rila@abv.bg. Поискайте оферта за контейнери и метални изделия.')

    def get_breadcrumbs(self):
        return [('Контакти', reverse('contacts:page'))]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(inquiry_form=InquiryForm(), contact_form=ContactMessageForm())
        return ctx


@require_POST
def inquiry(request):
    return _handle(request, InquiryForm,
                   'Благодарим ви! Ще ви изпратим оферта до един работен ден.')


@require_POST
def contact(request):
    return _handle(request, ContactMessageForm,
                   'Съобщението е изпратено. Ще се свържем с вас съвсем скоро.')
