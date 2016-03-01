import json
from .metadata import wrap_dict, wrap_raw_json

class Property(object):
    def __init__(self, type=str, name=None, default=None, enum=None,
                 required=False, validator=None, wrap=False, none=None):
        self.name = name
        self.type = enum if enum else type
        self.enum = enum
        self.required = required
        self.validator = validator
        self.default = default
        self.wrap = wrap
        self.none = none
    
    def __property_config__(self, model_class, property_name):
        self.model_class = model_class
        if self.name is None:
            self.name = property_name

    def __get__(self, model_instance, model_class):
        if model_instance is None:
            return self

        if self.type in (dict, list):
            try:
                return getattr(model_instance, self.attr_name)
            except AttributeError:
                value = self.type() if self.default is None else self.type(self.default)
                setattr(model_instance, self.attr_name, value)
                return value
        else:
            try:
                value = getattr(model_instance, self.attr_name)
                if value is None:
                    return self.none
                else:
                    return value
            except AttributeError:
                return self.default
    
    def __set__(self, model_instance, value):
        value = self.validate(value)
        setattr(model_instance, self.attr_name, value)
    
    def is_empty(self, value):
        return value is None

    def validate(self, value):
        if value is None and not self.required:
            return None

        # Bool
        try:
            if self.type is bool and value.lower() in ('yes', 'no', 'true', 'false', '1', '0'):
                if value in ('yes', 'true', '1'):
                    value = True
                else:
                    value = False
        except AttributeError:
            pass

        # PropertySet - Wrapped
        if self.wrap:
            if isinstance(value, dict):
                value = wrap_dict(value)
            elif isinstance(value, str):
                value = wrap_raw_json(value)

        # PropertySet - Direct
        elif issubclass(self.type, PropertySet) and isinstance(value, dict):
            value = self.type(value)

        # Enum
        elif self.enum:
            value = self.enum(value)

        # Built-ins
        elif self.type is int or self.type is float or self.type is str:
            value = self.type(value)

        # Required
        if self.required:
            if self.is_empty(value):
                raise ValueError("Property %s is required" % self.name)

        # Enum test
        if self.enum is not None:
            if not isinstance(value, self.enum):
                raise ValueError("Property %s must be enum of type %s" % (self.name, repr(self.enum)))
        
        # External Validator
        if callable(self.validator):
            self.validator(value)

        return value
    
    @property
    def attr_name(self):
        return '_' + self.name

    @property
    def is_embedded(self):
        return hasattr(self.type, 'to_dict') and callable(getattr(self.type, 'to_dict'))


def _initialize_properties(model_class, name, bases, dct):
    model_class._properties = {}
    
    property_source = {}
    def get_attr_source(name, cls):
        for src_cls in cls.mro():
            if name in src_cls.__dict__:
                return src_cls

    defined = set()

    for base in bases:
        if hasattr(base, '_properties'):
            property_keys = set(base._properties.keys())
            duplicate_property_keys = defined & property_keys
            for dupe_prop_name in duplicate_property_keys:
                old_source = property_source[dupe_prop_name] = get_attr_source(
                    dupe_prop_name, property_source[dupe_prop_name]
                )
                new_source = get_attr_source(dupe_prop_name, base)
                if old_source != new_source:
                    raise AttributeError(
                        'Duplicate property, %s, is inherited from both %s and %s.' %
                        (dupe_prop_name, old_source.__name__, new_source.__name__)
                     )

        property_keys -= duplicate_property_keys
        if property_keys:
            defined |= property_keys
            property_source.update(dict.fromkeys(property_keys, base))
            model_class._properties.update(base._properties)

    for attr_name in dct.keys():
        attr = dct[attr_name]
        if isinstance(attr, Property):
            if attr_name in defined:
                raise AttributeError('Duplicate property: %s' % attr_name)
            defined.add(attr_name)
            model_class._properties[attr_name] = attr
            attr.__property_config__(model_class, attr_name)

    model_class._all_properties = tuple(
        prop.name for name, prop in model_class._properties.items()
    )


class ClassWithProperties(type):
    def __init__(cls, name, bases, dct):
        super(ClassWithProperties, cls).__init__(name, bases, dct)
        _initialize_properties(cls, name, bases, dct)
        

class PropertySet(metaclass=ClassWithProperties):
    def __init__(self, *args, **values):
        if len(args) == 1:
            self.from_dict(args[0])
        for key, value in values.items():
            setattr(self, key, value)

    def to_json(self, pretty=True):
        return json.dumps(self, default=lambda x: x.to_dict(), indent=(2 if pretty else None), sort_keys=True)

    def from_json(self, json_string):
        if json_string is None:
            self.from_dict({})
        else:
            self.from_dict(json.loads(json_string))

    def to_dict(self):
        dct = {}
        for attr_name in self._all_properties:
            dct[attr_name] = getattr(self, attr_name)
        dct['*schema'] = self.__class__.__name__
        return dct

    def from_dict(self, dct):
        for attr_name in self._all_properties:
            if attr_name in dct:
                setattr(self, attr_name, dct.get(attr_name)) 

    def from_row(self, row):
        raise NotImplemented

    @classmethod
    def FromRow(cls, dct, prefix=None):
        if dct is not None:
            inst = cls()
            inst.from_row(dct, prefix=prefix)
            return inst

    @classmethod
    def FromJSON(cls, json_string):
        inst = cls()
        inst.from_json(json_string)
        return inst



def strip(dct, prefix):
    if prefix is None:
        return dct
    else:
        length = len(prefix) + 1
        return {k[length:]: dct[k] for k in dct.keys() if k.startswith(prefix + '.')}

def first(*objects):
    """
    Return the first non-None object in objects.
    """
    for obj in objects:
        if obj is not None:
            return obj
