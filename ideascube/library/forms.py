import re

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from .models import Book, BookSpecimen
from .utils import (fetch_from_openlibrary, load_from_ideascube,
                    load_from_moccam_csv, load_unimarc)


class BookSpecimenForm(forms.ModelForm):

    def clean_serial(self):
        # Keep only letters, and make sure empty values are mapped to None,
        # not empty string (we need NULL values in db, not empty strings, for
        # uniqueness constraints).
        return re.sub(r'\s', '', self.cleaned_data['serial']) or None

    def clean_file(self):
        # Ensure specimenfile and serial are not both filled or both set to
        # None.
        if all([self.cleaned_data['file'], self.cleaned_data['serial']]):
            raise ValidationError(_("You can't have both a file and a serial"))
        if not any([self.cleaned_data['file'], self.cleaned_data['serial']]):
            raise ValidationError(_("You must add a file or a serial"))
        return self.cleaned_data['file']

    class Meta:
        model = BookSpecimen
        widgets = {'book': forms.HiddenInput}
        fields = '__all__'


class BookForm(forms.ModelForm):

    def clean_isbn(self):
        # Keep only integers, and make sure empty values are mapped to None,
        # not empty string (we need NULL values in db, not empty strings, for
        # uniqueness constraints).
        return re.sub(r'\D', '', self.cleaned_data['isbn']) or None

    class Meta:
        model = Book
        fields = '__all__'


class ImportForm(forms.Form):

    MOCCAM_CSV = 'moccam_csv'
    UNIMARC = 'unimarc'
    IDEASCUBE = 'ideascube'
    FORMATS = (
        (MOCCAM_CSV, _('CSV from "Mocam-en-ligne"')),
        (UNIMARC, 'UNIMARC'),
        (IDEASCUBE, _('Ideascube ZIP')),
    )

    from_files = forms.FileField(required=False)
    files_format = forms.ChoiceField(choices=FORMATS)
    from_isbn = forms.CharField(widget=forms.Textarea, required=False)

    def save_from_files(self):
        """Create or update books from given metadata files."""
        files = self.cleaned_data['from_files']
        format_ = self.cleaned_data['files_format']
        if format_ == self.MOCCAM_CSV:
            handler = load_from_moccam_csv
        elif format_ == self.UNIMARC:
            handler = load_unimarc
        elif format_ == self.IDEASCUBE:
            handler = load_from_ideascube
        else:
            raise ValueError(_('Unknown file format'))
        books = []
        for notice, cover in handler(files):
            if not notice:
                continue
            notice.setdefault('section', Book.OTHER)
            notice.setdefault('lang', settings.LANGUAGE_CODE)
            isbn = notice.get('isbn')
            instance = None
            if isbn:
                instance = Book.objects.filter(isbn=isbn).first()
            form = BookForm(data=notice, files={'cover': cover},
                            instance=instance)
            if form.is_valid():
                book = form.save()
                books.append(book)
        return books

    def save_from_isbn(self):
        """Create or update books from given ISBN, using OpenLibrary API."""
        isbns = self.cleaned_data['from_isbn'].splitlines()
        books = []
        for isbn in isbns:
            notice = fetch_from_openlibrary(isbn)
            if not notice:
                continue
            notice['section'] = Book.OTHER
            book, _ = Book.objects.update_or_create(isbn=notice['isbn'],
                                                    defaults=notice)
            books.append(book)
        return books
