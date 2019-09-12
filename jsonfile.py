"""
The ``jsonfile`` Python module can be used to sync a JSON file
on a disk with the corresponding Python object instance.

Can be used to autosave JSON compatible Python data.
"""
__version__ = "0.0.1"



import collections.abc
import copy
import json
import pathlib
import tempfile



class JSONFileBase:

  def _get_adapter_or_value(self, data):
    if isinstance(data, collections.abc.Sequence):
      return JSONFileArray(self._root, data)
    elif isinstance(data, collections.abc.Mapping):
      return JSONFileObject(self._root, data)
    else:
      return data

  @staticmethod
  def _value_norm(value):
    if isinstance(value, collections.abc.Mapping):
      return {str(k): v for k, v in value.items()}
    else:
      return value



class JSONFile(JSONFileBase):

  def __init__(self, filepath, *,
      autosave=False,
      dump_kwargs = None,
      load_kwargs = None,
  ):
    self._root = self
    self.autosave = autosave
    self.dump_kwargs = dump_kwargs or dict(
        skipkeys=False,
        ensure_ascii=True,
        check_circular=True,
        allow_nan=True,
        cls=None,
        indent=None,
        separators=None,
        default=None,
        sort_keys=False,
    )
    self.load_kwargs = load_kwargs or dict(
        cls=None,
        object_hook=None,
        parse_float=None,
        parse_int=None,
        parse_constant=None,
        object_pairs_hook=None,
    )
    self.filepath = filepath  # creates self.data, self.changed

  @property
  def autosave(self):
    return bool(self._autosave)  # ensure boolean

  @autosave.setter
  def autosave(self, value):
    self._autosave = bool(value)  # ensure boolean

  @property
  def data(self):
    return self._get_adapter_or_value(self._data)

  @data.setter
  def data(self, value):
    if value is ...:
      raise ValueError("Ellipsis is forbidden, call delete()")
    old_data = copy.copy(self._data)
    self._data = self._value_norm(value)
    self.may_changed(self, old_data)

  @property
  def filepath(self):
    return self._filepath

  @filepath.setter
  def filepath(self, value):
    self._filepath = pathlib.Path(value) # ensure Path instance
    self.reload()  # creates self._data

  def delete(self):
    # could have been @data.deleter but that would be obscure
    old_data = copy.copy(self._data)
    self._data = ...
    self.may_changed(self, old_data)

  def may_changed(self, inst, old_data):
    if inst._data != old_data:
      self.changed = True
      if self.autosave:
        self.save()

  def reload(self):
    p = self.filepath
    if (
        p.is_file()  # filepath_exists
        and p.stat().st_size  # filepath_not_empty
    ):
      with p.open(encoding="utf8") as f:
        self._data = json.load(f, **self.load_kwargs)
        self.changed = False
    else:
        self._data = ...
        self.changed = None

  def save(self):
    p = self.filepath
    if self._data is ... and p.is_file():
      p.unlink()
    else:
      s = json.dumps(self._data, **self.dump_kwargs)
      with tempfile.NamedTemporaryFile(
          'w',
          dir = p.parent,
          delete = False,
      ) as tf:
        tf.write(s)
        tp = p.parent / tf.name
      tp.replace(p)



class JSONFileContainer(JSONFileBase):

  def __init__(self, root, data):
    self._root = root
    self._data = data

  def __delitem__(self, key):  # has to be explicit
    m = self._change_method("__delitem__")
    return m(key)

  def __dir__(self):
    return self._data.__dir__()

  @property
  def __doc__(self):
    return self._data.__doc__

  def __getattr__(self, name):
    if name in self._change_method_names:
      return self._change_method(name)
    else:
      return getattr(self._data, name)

  def __getitem__(self, key):
    data = self._data[key]
    return self._get_adapter_or_value(data)

  def __repr__(self):
    return self._data.__repr__()

  def __setitem__(self, key, value):  # has to be explicit
    m = self._change_method("__setitem__")
    return m(key, self._value_norm(value))

  def _change_method(self, name):
    def wrapped_method(*args, **kwargs):
      old_data = copy.copy(self._data)
      m = object.__getattribute__(self._data, name)
      try:
        r = m(*args, **kwargs)
        self._root.may_changed(self, old_data)
      except:
        self._data = old_data
        raise
      return r
    return wrapped_method



class JSONFileArray(JSONFileContainer):

  _change_method_names = (
    "__delitem__",
    "__iadd__",
    "__imul__",
    "__setitem__",
    "append",
    "clear",
    "extend",
    "insert",
    "pop",
    "remove",
    "reverse",
    "sort",
  )



class JSONFileObject(JSONFileContainer):

  _change_method_names = (
    "__delitem__",
    "__setitem__",
    "clear",
    "pop",
    "popitem",
    "setdefault",
    "update",
  )

  def __setitem__(self, key, value):  # has to be explicit
    key = str(key)  # JSON obejct keys must be strings
    return super().__setitem__(key, value)



jsonfile = JSONFile