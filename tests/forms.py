from django import forms

from multiform import MultiForm, MultiModelForm, InvalidArgument

from .models import Pizza, Topping


class EmptyForm(forms.Form):
    pass


class FooForm(forms.Form):
    foo = forms.CharField()


class HiddenForm(forms.Form):
    bar = forms.CharField(widget=forms.HiddenInput)


class MediaForm(forms.Form):
    class Media:
        js = ('tests.js',)


class MultipartForm(forms.Form):
    file = forms.FileField(required=False)


class CapturingForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.captured = kwargs.pop('capture', None)
        super(CapturingForm, self).__init__(*args, **kwargs)


class ValidationErrorForm(forms.Form):
    def clean(self):
        raise forms.ValidationError('error')


class InitialForm(forms.Form):
    baz = forms.CharField(initial='baz', required=False)


class PizzaModelForm(forms.ModelForm):
    class Meta:
        model = Pizza
        fields = ('name',)


class PizzaWithRestaurantModelForm(forms.ModelForm):
    class Meta:
        model = Pizza
        fields = ('name', 'restaurant')


class ToppingModelForm(forms.ModelForm):
    class Meta:
        model = Topping
        fields = ('name',)


SAMPLE_FORMS = [
    ('empty', EmptyForm),
    ('capture', CapturingForm),
    ('media', MediaForm),
    ('foo', FooForm),
]


class SampleMultiForm(MultiForm):
    base_forms = SAMPLE_FORMS


class MultiFormWithHiddenFields(MultiForm):
    base_forms = [
        ('foo', FooForm),
        ('hidden', HiddenForm),
    ]


class MultiFormWithInvalidArgument(MultiForm):
    base_forms = [
        ('foo', FooForm),
        ('capture', CapturingForm),
    ]

    def dispatch_init_capture(self, name, captured):
        if name == "capture":
            return captured
        return InvalidArgument


class MultiFormWithFileInput(MultiForm):
    base_forms = [
        ('multipart', MultipartForm),
    ]


class MultiFormWithNonFieldError(MultiForm):
    base_forms = [
        ('error', ValidationErrorForm)
    ]


class MultiFormWithInitial(MultiForm):
    base_forms = [
        ('initial', InitialForm),
    ]


class ToppingMultiModelForm(MultiModelForm):
    base_forms = {
        'pizza': PizzaModelForm,
        'topping': ToppingModelForm,
    }

    def dispatch_init_instance(self, name, instance):
        if name == 'topping':
            return instance
        return super(ToppingMultiModelForm, self) \
            .dispatch_init_instance(name, instance)


class ToppingPizzaRestaurantMultiModelForm(MultiModelForm):
    base_forms = {
        'pizza': PizzaWithRestaurantModelForm,
        'topping': ToppingModelForm,
    }

    def dispatch_init_instance(self, name, instance):
        if name == 'topping':
            return instance
        return super(ToppingPizzaRestaurantMultiModelForm, self) \
            .dispatch_init_instance(name, instance)
