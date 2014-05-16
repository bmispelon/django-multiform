from collections import OrderedDict

from django import test
from django.core.exceptions import ImproperlyConfigured

from multiform import MultiForm

from .forms import (
    EmptyForm,
    SampleMultiForm,
    MultiFormWithHiddenFields,
    MultiFormWithInvalidArgument,
    MultiFormWithFileInput,
    MultiFormWithNonFieldError,
    MultiFormWithInitial,
    SAMPLE_FORMS,

    ToppingMultiModelForm,
    ToppingPizzaRestaurantMultiModelForm,
)
from .models import Pizza, Restaurant, Topping


def make_multiform(base_forms=None, base=MultiForm, name="<test>"):
    return type(name, (base,), {'base_forms': base_forms})


class TestMultiForm(test.TestCase):

    def test_improperly_configured(self):
        """
        Try to initialize a multiform subclass with empty base_forms values.
        """
        with self.assertRaises(ImproperlyConfigured):
            make_multiform()()
        with self.assertRaises(ImproperlyConfigured):
            make_multiform([])()
        with self.assertRaises(ImproperlyConfigured):
            make_multiform({})()

    def test_init_too_many_positional_args(self):
        with self.assertRaises(TypeError):
            args = [None] * 20
            SampleMultiForm(*args)

    def test_init_duplicate_param(self):
        """
        Check that passing an argument both as positional and named fails.
        """
        with self.assertRaises(TypeError):
            # data is the first argument of the signature
            SampleMultiForm(None, data=None)

    def test_base_forms(self):
        """
        Check that various types are accepted for the base_forms attribute.
        """
        expected = sorted(name for name, form_class in SAMPLE_FORMS)

        for base_forms in [
            SAMPLE_FORMS,  # list of 2-tuple
            dict(SAMPLE_FORMS),
            OrderedDict(SAMPLE_FORMS)
        ]:
            form = make_multiform(base_forms)()
            self.assertEqual(expected, sorted(form.forms))

    def test_dispatch_kwargs(self):
        form = SampleMultiForm()
        self.assertIs(None, form['capture'].captured)
        form = SampleMultiForm(capture__capture='hello')
        self.assertEquals('hello', form['capture'].captured)

    def test_dispatch_kwargs_not_provided(self):
        form = MultiFormWithInvalidArgument()
        self.assertIs(None, form['capture'].captured)
        self.assertFalse(hasattr(form['foo'], 'captured'))
        form = MultiFormWithInvalidArgument(capture='hello')
        self.assertEquals('hello', form['capture'].captured)
        self.assertFalse(hasattr(form['foo'], 'captured'))

    def test_getitem(self):
        form = SampleMultiForm()
        self.assertIsInstance(form['empty'], EmptyForm)

    def test_iter(self):
        form = SampleMultiForm()
        self.assertEqual([f.name for f in form], ['foo'])

    def test_as_ul(self):
        form = SampleMultiForm()
        expected = ('<li><label for="id_foo-foo">Foo:</label> '
                    '<input id="id_foo-foo" name="foo-foo" type="text" />'
                    '</li>')
        self.assertHTMLEqual(form.as_ul().strip(), expected)

    def test_as_table(self):
        form = SampleMultiForm()
        expected = ('<tr><th><label for="id_foo-foo">Foo:</label></th>'
                    '<td><input id="id_foo-foo" name="foo-foo" type="text" />'
                    '</td></tr>')
        self.assertHTMLEqual(form.as_table().strip(), expected)

    def test_as_p(self):
        form = SampleMultiForm()
        expected = ('<p><label for="id_foo-foo">Foo:</label> '
                    '<input id="id_foo-foo" name="foo-foo" type="text" /></p>')
        self.assertHTMLEqual(form.as_p().strip(), expected)

    def test_nonfield_errors(self):
        form = MultiFormWithNonFieldError({})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(), {'error': ['error']})

    def test_is_valid(self):
        form = SampleMultiForm()
        self.assertFalse(form.is_valid())
        form = SampleMultiForm({})
        self.assertFalse(form.is_valid())
        form = SampleMultiForm({'foo-foo': 'yes'})
        self.assertTrue(form.is_valid())

    def test_cleaned_data(self):
        form = SampleMultiForm({'foo-foo': 'yes'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data, {
            'empty': {},
            'capture': {},
            'media': {},
            'foo': {'foo': 'yes'},
        })

    def test_changed_data(self):
        form = MultiFormWithInitial({'initial-baz': 'hello'})
        self.assertEqual(form.changed_data, {'initial': ['baz']})

    def test_media(self):
        form = SampleMultiForm()
        expected = '<script type="text/javascript" src="tests.js"></script>'
        self.assertHTMLEqual(str(form.media), expected)

    def test_multipart(self):
        form = SampleMultiForm()
        self.assertFalse(form.is_multipart())
        form = MultiFormWithFileInput()
        self.assertTrue(form.is_multipart())

    def test_hidden_fields(self):
        form = MultiFormWithHiddenFields()
        self.assertEqual([f.name for f in form.hidden_fields()], ['bar'])

    def test_visible_fields(self):
        form = MultiFormWithHiddenFields()
        self.assertEqual([f.name for f in form.visible_fields()], ['foo'])


class TestMultiModelForm(test.TestCase):

    def test_dispatch_instance_none(self):
        """When passing instance=None, an empty object is created."""
        form = ToppingMultiModelForm()
        self.assertIs(form['pizza'].instance.pk, None)
        self.assertEqual(form['pizza'].instance.name, '')
        self.assertIs(form['topping'].instance.pk, None)
        self.assertEqual(form['topping'].instance.name, '')

    def test_dispatch_instance(self):
        pizza = Pizza.objects.create(name='Plain')
        topping = Topping.objects.create(pizza=pizza, name='tomato sauce')
        form = ToppingMultiModelForm(instance=topping)
        self.assertEqual(form['pizza'].instance, pizza)
        self.assertEqual(form['topping'].instance, topping)

    def test_save(self):
        data = {'topping-name': 'tomato sauce', 'pizza-name': 'Plain'}
        form = ToppingMultiModelForm(data)
        self.assertTrue(form.is_valid())
        d = form.save(commit=False)
        d['pizza'].save()
        d['topping'].pizza = d['pizza']
        d['topping'].save()
        self.assertEqual(d['topping'], Topping.objects.get())
        self.assertEqual(d['pizza'], Pizza.objects.get())

    def test_save_m2m(self):
        restaurant = Restaurant.objects.create(name='Alfredo')
        data = {
            'topping-name': 'tomato sauce',
            'pizza-name': 'Plain',
            'pizza-restaurant': [restaurant.id]
        }
        form = ToppingPizzaRestaurantMultiModelForm(data)
        self.assertTrue(form.is_valid())
        d = form.save(commit=False)
        d['pizza'].save()
        d['topping'].pizza = d['pizza']
        d['topping'].save()
        form.save_m2m()
        self.assertEqual(d['topping'], Topping.objects.get())
        self.assertEqual(d['pizza'].restaurant.get(), Restaurant.objects.get())
        self.assertEqual(d['pizza'], Pizza.objects.get())
