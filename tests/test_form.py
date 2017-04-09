import os

import pytest
from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile

from hierarkey.forms import HierarkeyForm
from .testapp.models import GlobalSettings, Organization, hierarkey


class TestForm(HierarkeyForm):
    test_string = forms.CharField(max_length=100, required=False)
    test_int = forms.IntegerField(required=False)
    test_file = forms.FileField(required=False)


@pytest.fixture
def organization():
    return Organization.objects.create(name='Foo')


@pytest.mark.django_db
def test_form_defaults(organization):
    hierarkey.add_default('test_string', 'hallo')
    form = TestForm(obj=organization, attribute_name='settings')
    assert form.initial['test_string'] == 'hallo'


@pytest.mark.django_db
def test_form_initial_values(organization):
    hierarkey.add_default('test_string', 'hallo')
    organization.settings.test_string = 'bar'
    form = TestForm(obj=organization, attribute_name='settings')
    assert form.initial['test_string'] == 'bar'


@pytest.mark.django_db
def test_form_save_plain_values(organization):
    form = TestForm(obj=organization, attribute_name='settings', data={
        'test_string': 'foobar',
        'test_int': 42
    })
    assert form.is_valid()
    form.save()
    organization.settings.flush()
    assert organization.settings.test_string == 'foobar'
    assert organization.settings.test_int == '42'


@pytest.mark.django_db
def test_form_save_new_file(organization):
    val = SimpleUploadedFile("sample_invalid_image.jpg", b"file_content", content_type="image/jpeg")
    form = TestForm(obj=organization, attribute_name='settings', data={}, files={
        'test_file': val
    })
    assert form.is_valid()
    form.save()
    organization.settings.flush()
    assert organization.settings.get('test_file', as_type=str).startswith('file://')
    assert organization.settings.get('test_file', as_type=str).endswith(val.name)
    assert organization.settings.get('test_file', as_type=str).endswith(val.name)
    assert os.path.exists(organization.settings.get('test_file', as_type=File, binary_file=True).name)


@pytest.mark.django_db
def test_form_save_replaced_file(organization):
    val = SimpleUploadedFile("sample_invalid_image.jpg", b"file_content", content_type="image/jpeg")
    form = TestForm(obj=organization, attribute_name='settings', data={}, files={
        'test_file': val
    })
    assert form.is_valid()
    form.save()

    organization.settings.flush()
    oldname = organization.settings.get('test_file', as_type=File, binary_file=True).name

    val = SimpleUploadedFile("sample_invalid_image.jpg", b"file_content_2", content_type="image/jpeg")
    form = TestForm(obj=organization, attribute_name='settings', data={}, files={
        'test_file': val
    })
    assert form.is_valid()
    form.save()

    organization.settings.flush()
    assert os.path.exists(organization.settings.get('test_file', as_type=File, binary_file=True).name)
    assert organization.settings.get('test_file', as_type=File, binary_file=True).name != oldname
    assert not os.path.exists(oldname)


@pytest.mark.django_db
def test_form_save_unchanged_file(organization):
    val = SimpleUploadedFile("sample_invalid_image.jpg", b"file_content", content_type="image/jpeg")
    form = TestForm(obj=organization, attribute_name='settings', data={}, files={
        'test_file': val
    })
    assert form.is_valid()
    form.save()

    organization.settings.flush()
    oldname = organization.settings.get('test_file', as_type=File, binary_file=True).name

    form = TestForm(obj=organization, attribute_name='settings', data={'unaffected': 'on'}, files={})
    assert form.is_valid()
    form.save()

    organization.settings.flush()
    assert organization.settings.get('test_file', as_type=File, binary_file=True).name == oldname


@pytest.mark.django_db
def test_form_delete_file(organization):
    val = SimpleUploadedFile("sample_invalid_image.jpg", b"file_content", content_type="image/jpeg")
    form = TestForm(obj=organization, attribute_name='settings', data={}, files={
        'test_file': val
    })
    assert form.is_valid()
    form.save()

    organization.settings.flush()
    oldname = organization.settings.get('test_file', as_type=File, binary_file=True).name

    form = TestForm(obj=organization, attribute_name='settings', data={
        'test_file-clear': 'on'
    })
    assert form.is_valid()
    form.save()

    organization.settings.flush()
    assert not organization.settings.test_file
    assert not os.path.exists(oldname)
