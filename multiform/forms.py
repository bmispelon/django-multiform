from __future__ import unicode_literals

from collections import defaultdict, OrderedDict
from itertools import chain
from functools import reduce

import operator

from django.core.exceptions import ImproperlyConfigured
from django.forms.forms import BaseForm
from django.forms.util import ErrorList
from django.forms.widgets import Media
from django.utils.safestring import mark_safe


class MultiForm(BaseForm):
    """
    A BaseForm subclass that can wrap several sub-forms into one entity.
    To use it, define a `base_forms` attribute which should be a mapping
    (dict or collections.OrderedDict for example).
    It can then be used like a regular form.
    """

    base_fields = None  # Needed to bypass the absence of fancy metaclass
    _baseform_signature = OrderedDict([  # TODO: signature objects (pep 362)
        ('data', None),
        ('files', None),
        ('auto_id', 'id_%s'),
        ('prefix', None),
        ('initial', None),
        ('error_class', ErrorList),
        ('label_suffix', ':'),
        ('empty_permitted', False),
    ])

    def __init__(self, *args, **kwargs):
        sig_kwargs, extra_kwargs = self._normalize_init_signature(args, kwargs)
        self._init_parent(**sig_kwargs)
        self._init_wrapped_forms(sig_kwargs, extra_kwargs)

    def _init_parent(self, **kwargs):
        super(MultiForm, self).__init__(**kwargs)

    def _normalize_init_signature(self, args, kwargs):
        """
        Put all the given arguments to __init__ into a dict, whether they were
        passed as positional arguments or keyword ones.
        Return two dictionaries: the normalized init arguments and another one
        with the extra ones (not part of the signature).
        """
        if len(args) > len(self._baseform_signature):
            msg = "%s.__init__ got too many positional arguments."
            raise TypeError(msg % self.__class__)

        normalized_kwargs = self._baseform_signature.copy()

        for k, v in zip(self._baseform_signature, args):
            if k in kwargs:
                msg = "%s.__init__ got multiple values for argument '%s'"
                raise TypeError(msg % (self.__class__, k))
            normalized_kwargs[k] = v

        for k in list(self._baseform_signature)[len(args):]:  # remaining ones
            try:
                normalized_kwargs[k] = kwargs.pop(k)
            except KeyError:
                pass

        # at this point, ``kwargs`` only contain keys that are not
        # in the form's signature
        return normalized_kwargs, kwargs

    def _init_wrapped_forms(self, sig_kwargs, extra_kwargs):
        """
        Initialize the wrapped forms by passing the ones received in __init__
        and adding the keyword arguments whose names look like `$name__*`.
        """
        base_forms = self.get_base_forms()
        # We start by extracting all the keyword parameters that look like
        # "$name__*" where $name is the name of one of the wrapped form.
        # With this, we build a mapping of (name -> stripped_kwargs)
        # where the stripped_kwargs have been stripped off of the form's name.
        dispatched_kwargs = defaultdict(dict)
        for k in list(extra_kwargs):  # Because we mutate it
            prefix, _, remainder = k.partition('__')
            if remainder and prefix in base_forms:
                dispatched_kwargs[prefix][remainder] = extra_kwargs.pop(k)

        # Any extra_kwargs left at this point will be passed as-is to all
        # wrapped forms.

        self.forms = OrderedDict()
        for name, form_class in base_forms.items():
            # We build each wrapped form one by one.
            # Their keyword arguments are built in three steps, each with
            # precedence over the next one:
            # 1) For all the keywords that are part of the normal signature,
            #    we check for the presence of a dispatch_init_$keyword method
            #    on the instance.
            #    If no such method is present, we just pass the value of the
            #    argument as-is.
            #    If such a method exists, then we use the result of calling
            #    this method, passing the form's name and the original value.
            # 2) Any existing ``extra_kwargs`` are applied.
            # 3) If some dispatched_kwargs exist for this method (that is,
            # keyword arguments passed to the MultiForm's __init__ whose name
            # look like "$name__*"), then they are applied.
            kwargs = {}
            for k, v in sig_kwargs.items():
                if hasattr(self, 'dispatch_init_%s' % k):
                    kwargs[k] = getattr(self, 'dispatch_init_%s' % k)(name, v)
                else:
                    kwargs[k] = v
            kwargs.update(extra_kwargs)
            kwargs.update(dispatched_kwargs[name])
            self.forms[name] = form_class(**kwargs)

    def dispatch_init_prefix(self, name, prefix):
        """
        When instanciating a wrapped form, we add its name to the given prefix.
        """
        # prefix is already stored on self.prefix by super().__init__,
        # so self.add_prefix works.
        return self.add_prefix(name)

    def get_base_forms(self):
        """
        Return a mapping of the forms that this multiform wraps (name -> form).
        """
        if not getattr(self, 'base_forms', None):
            error_message_fmt = "%s does not define a base_forms attribute."
            raise ImproperlyConfigured(error_message_fmt % self.__class__)

        # Incidentally, this also makes a shallow copy
        return OrderedDict(self.base_forms)

    def _combine(self, attr, filter=False,
                 call=False, call_args=(), call_kwargs=None):
        """
        Combine an attribute (or method) of each wrapped form into an
        OrderedDict.
        To remove empty vales from the dict, pass ``filer=False``.
        To call a method, pass ``call=True`` (passing ``call_args`` and
        ``call_kwargs`` if needed).
        """
        if not call_kwargs:
            call_kwargs = {}
        d = OrderedDict()
        for name, form in self.forms.items():
            v = getattr(form, attr)
            if call:
                v = v(*call_args, **call_kwargs)
            if not filter or v:
                d[name] = v
        return d

    def _combine_values(self, *args, **kwargs):
        """
        Similar to _combine, but only return the values, not the full dict.
        """
        return self._combine(*args, **kwargs).values()

    def _combine_chain(self, *args, **kwargs):
        """Use itertools.chain on the combined values."""
        return chain.from_iterable(self._combine_values(*args, **kwargs))

    # All BaseForm's public methods and properties are implemented next.
    # Basically, a call to a MultiForm's method gets dispatched to all the
    # wrapped forms and the results get collected either in an OrderedDict
    # or in a list.

    def __iter__(self):
        return chain.from_iterable(self._combine_values('__iter__', call=True))

    def __getitem__(self, name):
        return self.forms[name]

    def _html_output(self, *args, **kwargs):
        rendered = self._combine_values('_html_output', call=True, filter=True,
                                        call_args=args, call_kwargs=kwargs)
        return mark_safe('\n'.join(rendered))

    def non_field_errors(self):
        return self._combine('non_field_errors', call=True, filter=True)

    def full_clean(self):
        # This will call full_clean on all sub-forms
        # (and populate their _errors attribute):
        self._errors = self._combine('errors', filter=True)

        if not self._errors:
            # Each sub-form's cleaned_data is now populated
            self.cleaned_data = self._combine('cleaned_data')

    @property
    def changed_data(self):
        return self._combine('changed_data', filter=True)

    @property
    def media(self):
        return reduce(operator.add, self._combine_values('media'), Media())

    def is_multipart(self):
        return any(self._combine_values('is_multipart', call=True))

    def hidden_fields(self):
        return list(self._combine_chain('hidden_fields', call=True))

    def visible_fields(self):
        return list(self._combine_chain('visible_fields', call=True))


class MultiModelForm(MultiForm):
    """
    A MultiForm that supports a ModelForm's signature.
    Also implements a save method.
    """
    _baseform_signature = OrderedDict(
        list(MultiForm._baseform_signature.items()) + [('instance', None)])

    def _init_parent(self, **kwargs):
        del kwargs['instance']
        super(MultiForm, self).__init__(**kwargs)

    def dispatch_init_instance(self, name, instance):
        if instance is None:
            return None
        return getattr(instance, name)

    def save(self, commit=True):
        # TODO: Find a good API to wrap this in a db transaction
        # TODO: allow committing some forms but not others
        return self._combine('save', call=True, call_kwargs={'commit': commit})
