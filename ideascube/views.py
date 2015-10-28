import csv
import mimetypes
import socket
import StringIO
import urllib2
from datetime import datetime
from urlparse import urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, authenticate, login
from django.contrib.auth.forms import SetPasswordForm
from django.core.urlresolvers import reverse_lazy
from django.core.validators import URLValidator, ValidationError
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseRedirect)
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext as _
from django.views.generic import (CreateView, DeleteView, DetailView, FormView,
                                  ListView, UpdateView, View)
from taggit.models import TaggedItem

from ideascube.blog.models import Content
from ideascube.decorators import staff_member_required
from ideascube.library.models import Book
from ideascube.mediacenter.models import Document

from .forms import UserForm, CreateStaffForm

user_model = get_user_model()


def index(request):
    if not user_model.objects.filter(is_staff=True).exists():
        return HttpResponseRedirect(reverse_lazy('welcome_staff'))
    content = Content.objects.published().order_by('published_at').first()
    random_book = Book.objects.available().order_by('?').first()
    random_doc = Document.objects.order_by('?').first()
    context = {
        'blog_content': content,
        'random_book': random_book,
        'random_doc': random_doc,
        'cards': settings.HOME_CARDS,
        'domain': settings.DOMAIN,
    }
    return render(request, 'index.html', context)


def welcome_staff(request):
    """Allow to create a staff user if None exists yet."""
    if user_model.objects.filter(is_staff=True).exists():
        return HttpResponseRedirect('/')
    if request.method == 'POST':
        form = CreateStaffForm(request.POST)
        if form.is_valid():
            user = form.save()
            user = authenticate(serial=user.serial,
                                password=request.POST['password'])
            login(request, user)
            msg = _('Welcome to {}, {}!').format(settings.IDEASCUBE_NAME, user)
            messages.add_message(request, messages.SUCCESS, msg)
            return HttpResponseRedirect('/')
    else:
        form = CreateStaffForm()
    return render(request, 'ideascube/welcome_staff.html', {'form': form})


class ByTag(ListView):
    template_name = 'ideascube/by_tag.html'
    paginate_by = 20

    def get_queryset(self):
        return TaggedItem.objects.filter(tag__slug=self.kwargs['tag'])

by_tag = ByTag.as_view()


class UserList(ListView):
    model = user_model
    template_name = 'ideascube/user_list.html'
    context_object_name = 'user_list'
    paginate_by = 50

    def get_context_data(self, **kwargs):
        context = super(UserList, self).get_context_data(**kwargs)
        context['USERS_LIST_EXTRA_FIELDS'] = settings.USERS_LIST_EXTRA_FIELDS
        context['q'] = self.request.GET.get('q', '')
        return context

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return self.model.objects.search(query)
        else:
            return super(UserList, self).get_queryset()

user_list = staff_member_required(UserList.as_view())


class UserDetail(DetailView):
    model = user_model
    template_name = 'ideascube/user_detail.html'
    context_object_name = 'user_obj'
user_detail = staff_member_required(UserDetail.as_view())


class UserFormMixin(object):

    def get_context_data(self, *args, **kwargs):
        context = super(UserFormMixin, self).get_context_data(*args, **kwargs)
        context['USER_FORM_FIELDS'] = settings.USER_FORM_FIELDS
        return context


class UserUpdate(UserFormMixin, UpdateView):
    model = user_model
    template_name = 'ideascube/user_form.html'
    context_object_name = 'user_obj'
    form_class = UserForm
user_update = staff_member_required(UserUpdate.as_view())


class UserCreate(UserFormMixin, CreateView):
    model = user_model
    template_name = 'ideascube/user_form.html'
    context_object_name = 'user_obj'
    form_class = UserForm
user_create = staff_member_required(UserCreate.as_view())


class UserDelete(DeleteView):
    model = user_model
    template_name = 'ideascube/user_confirm_delete.html'
    context_object_name = 'user_obj'
    success_url = reverse_lazy('user_list')
user_delete = staff_member_required(UserDelete.as_view())


class UserToggleStaff(View):

    def get(self, *args, **kwargs):
        self.user = get_object_or_404(user_model, pk=self.kwargs['pk'])
        self.user.is_staff = not self.user.is_staff
        self.user.save()
        return HttpResponseRedirect(self.user.get_absolute_url())
user_toggle_staff = staff_member_required(UserToggleStaff.as_view())


class SetPassword(FormView):
    form_class = SetPasswordForm
    template_name = 'ideascube/set_password.html'

    def get_form_kwargs(self):
        kwargs = super(SetPassword, self).get_form_kwargs()
        kwargs['user'] = get_object_or_404(user_model, pk=self.kwargs['pk'])
        return kwargs

    def form_valid(self, form):
        form.save()
        msg = _('Password has been set for {user}').format(user=form.user)
        messages.add_message(self.request, messages.SUCCESS, msg)
        return super(SetPassword, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('user_detail', kwargs=self.kwargs)

set_password = staff_member_required(SetPassword.as_view())


class CSVExportMixin(object):

    prefix = 'idb'

    def render_to_csv(self):
        out = StringIO.StringIO()
        headers = self.get_headers()
        writer = csv.DictWriter(out, headers)
        writer.writeheader()
        for item in self.get_items():
            row = self.get_row(item)
            writer.writerow(row)
        out.seek(0)
        response = HttpResponse(out.read())
        filename = self.get_filename()
        attachment = 'attachment; filename="{name}.csv"'.format(name=filename)
        response['Content-Disposition'] = attachment
        response['Content-Type'] = 'text/csv'
        return response

    def get_item(self):
        raise NotImplementedError('CSVExportMixin needs a get_items method')

    def get_headers(self):
        raise NotImplementedError('CSVExportMixin needs a get_headers method')

    def get_filename(self):
        filename = "_".join([
            self.prefix,
            settings.IDEASCUBE_ID,
            str(datetime.now())
        ])
        return filename


class UserExport(CSVExportMixin, View):

    def get(self, *args, **kwargs):
        return self.render_to_csv()

    def get_items(self):
        return user_model.objects.all()

    def get_headers(self):
        self.fields = user_model.get_data_fields()
        return [unicode(f.verbose_name).encode('utf-8') for f in self.fields]

    def get_row(self, user):
        data_fields = user.data_fields
        row = {}
        for field in self.fields:
            value = data_fields[field.name]['value']
            if value is None:
                value = ''
            value = unicode(value).encode('utf-8')
            row[unicode(field.verbose_name).encode('utf-8')] = value
        return row
user_export = staff_member_required(UserExport.as_view())


def validate_url(request):
    assert request.method == "GET"
    assert request.is_ajax()
    url = request.GET.get('url')
    assert url
    try:
        URLValidator(url)
    except ValidationError:
        raise AssertionError()
    assert 'HTTP_REFERER' in request.META
    toproxy = urlparse(url)
    assert toproxy.hostname
    if settings.DEBUG:
        return url
    referer = urlparse(request.META.get('HTTP_REFERER'))
    assert referer.hostname == request.META.get('SERVER_NAME')
    assert toproxy.hostname != "localhost"
    try:
        # clean this when in python 3.4
        ipaddress = socket.gethostbyname(toproxy.hostname)
    except:
        raise AssertionError()
    assert not ipaddress.startswith('127.')
    assert not ipaddress.startswith('192.168.')
    return url


class AjaxProxy(View):

    def get(self, *args, **kwargs):
        # You should not use this in production (use Nginx or so)
        try:
            url = validate_url(self.request)
        except AssertionError as e:
            return HttpResponseBadRequest()
        headers = {
            'User-Agent': 'ideascube +http://ideas-box.org'
        }
        request = urllib2.Request(url, headers=headers)
        opener = urllib2.build_opener()
        try:
            proxied_request = opener.open(request)
        except urllib2.HTTPError as e:
            return HttpResponse(e.msg, status=e.code,
                                content_type='text/plain')
        else:
            status_code = proxied_request.code
            mimetype = (proxied_request.headers.typeheader
                        or mimetypes.guess_type(url))
            content = proxied_request.read()
            # Quick hack to prevent Django from adding a Vary: Cookie header
            self.request.session.accessed = False
            return HttpResponse(content, status=status_code,
                                content_type=mimetype)
ajax_proxy = AjaxProxy.as_view()


def javascript(request):
    response = render(request, 'ideascube/includes/js.html',
                      {'settings': settings})
    response['Content-Type'] = 'text/javascript'
    return response