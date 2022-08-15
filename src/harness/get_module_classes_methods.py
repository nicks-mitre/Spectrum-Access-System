# from usefulPythonShellFunctions import filterGlobalsListByType
import typing, re, sys, copy, importlib
from inspect import signature as get_signature
from typing import Optional, Union, Dict, List, Tuple, Any, Type
from types import ModuleType, FunctionType

OptStr = Optional[str]  # == Union[str, NoneType]


def _accept_module_or_str(
	module: Union[ModuleType, str],
	reload_module: bool = False
) -> ModuleType:
	"""
	:param module: either a module object on which to operate, or the name of (path to) a module file on which to temporarily import
	:param reload_module: If True (False by default), then the function will reload the given module (which must have been previously imported) to use any changes to the module since it was imported.
	"""
	if isinstance(module, str):
		mod_name = module.replace('.py', '')
		if mod_name in globals().keys():
			if reload_module:
				mod = importlib.reload(globals()[mod_name])
			else:
				mod = globals()[mod_name]
		else:
			mod = importlib.import_module(mod_name)
	elif isinstance(module, ModuleType):
		mod = module
	else:
		raise TypeError(f"module must be of type ModuleType or str. Received type: {type(module)}")

	return mod


def _getVarsInfoList(obj: Optional[Any] = None) -> List[Tuple[str, str, Union[str, int], int]]:
	"""
	Returns a list of tuples containing information about objects in one of the following:
	global symbol table (if called without an argument - default)
	object obj's __dict__ (if called with an argument)
	"""
	itemsList = []
	infoList = []  # The list to be returned

	if obj is None:
		# If the function is called without args, the function uses the global symtable
		itemsList = globals().items()
	else:
		# Otherwise, it uses the symtable of the obj
		try:
			itemsList = vars(obj).items()
		except TypeError:
			# TODO: Implement __slots__ check and return that instead.
			# TypeError: vars() argument must have __dict__ attribute
			return infoList

	for k, v in itemsList:
		vLen = '—'  # displayed length for values that aren't Sized

		# typing.Sized is "an alias to collections.abc.Sized," which is an "[abstract base class] for classes
		# that provide the __len__() method."
		if isinstance(v, typing.Sized):
			# vLen = str(len(v))
			vLen = len(v)

		sizeInBytes = sys.getsizeof(v)
		tupToAppend = (k, type(v), vLen, sizeInBytes)
		infoList.append(tupToAppend)

	return infoList


def _filterGlobalsListByType(
	desiredType: Type,
	obj: Optional[Any] = None,
	include_subclasses: bool = True
) -> List[Tuple[str, str, Union[str, int], int]]:
	"""
	Returns a list of tuples containing information about the (non-IPython-related) objects of type desiredType in the
	globals dict. :param desiredType: A typing.Type object (e.g. 'desiredType=FunctionType' is equivalent to
	'desiredType=type(getVarsInfoList)') that specifies which objects to include in the returned list. :param obj:
	Optional parameter specifying that
	"""
	if not (isinstance(desiredType, Type) or isinstance(desiredType, typing._GenericAlias)):
		raise TypeError("desiredType must be of type Type")

	itemsList = []
	if (obj is not None) and (len(_getVarsInfoList(obj)) > 0):
		for tup in _getVarsInfoList(obj):
			if not include_subclasses:
				if isinstance(tup[1], desiredType):
					itemsList.append(tup)
			else:
				# issubclass(TypeA, TypeA) is True
				if issubclass(tup[1], desiredType):
					itemsList.append(tup)

	elif len(_getVarsInfoList()) > 0:
		for tup in _getVarsInfoList():
			if not include_subclasses:
				if isinstance(tup[1], desiredType):
					itemsList.append(tup)
			else:
				if issubclass(tup[1], desiredType):
					itemsList.append(tup)

	return itemsList


def get_module_classes(
	module: Union[ModuleType, str],
	reload_module: bool = False,
	sort: bool = True
) -> List[str]:
	"""
	Returns a list of the classes defined in (or imported by) the given module.
	:param module: either a module object on which to operate, or the name of (path to) a module file on which to temporarily import
	:param reload_module: If True (False by default), then the function will reload the given module (which must have been previously imported) to use any changes to the module since it was imported.
	:param sort: If True (default), returns the list of classes sorted in alphabetical order. Otherwise, the list is in the order that the classes were defined/imported.
	"""
	mod = _accept_module_or_str(module, reload_module)

	filt_classes = _filterGlobalsListByType(obj=mod, desiredType=typing.Type)
	classes = [t[0] for t in filt_classes]
	if sort:
		return sorted(classes)
	else:
		return classes


def get_module_classes_methods(
	module: Union[ModuleType, str],
	reload_module: bool = False
) -> Dict:
	"""
	For each class in the given module, create a dictionary key-value pair with the key being the name of the class, and the value being a list of the methods for that class.
	:param module: either a module object on which to operate, or the name of (path to) a module file on which to temporarily import
	:param reload_module: If True (False by default), then the function will reload the given module (which must have been previously imported) to use any changes to the module since it was imported.
	"""
	mod = _accept_module_or_str(module, reload_module)

	classes = get_module_classes(mod, False)

	cls_method_mapping = { }

	for i in classes:
		filt_funcs = _filterGlobalsListByType(
			obj=getattr(mod, i),
			desiredType=FunctionType
		)
		funcs = sorted([t[0] for t in filt_funcs])

		cls_method_mapping.update({ i: funcs })

	return cls_method_mapping


def get_module_type_aliases(
	module: Union[ModuleType, str],
	reload_module: bool = False
) -> Dict:
	"""
	Returns a list of type aliases defined (or used) in the given module.
	:param module: either a module object on which to operate, or the name of (path to) a module file on which to temporarily import
	:param reload_module: If True (False by default), then the function will reload the given module (which must have been previously imported) to use any changes to the module since it was imported.
	"""
	mod = _accept_module_or_str(module, reload_module)

	filt_aliases = _filterGlobalsListByType(obj=mod, desiredType=typing._GenericAlias)

	# without sorting, the aliases are in the order they were defined,
	#   which allows us to substitute sub-components of more complex type hints
	#   with the an alias matching that component.
	aliases = [t[0] for t in filt_aliases]

	return { k: getattr(mod, k) for k in aliases }


# for a string like 'typing.Dict[str, object.typing.List[typing.Dict]]',
#   matches 'typing', 'object.typing', and 'typing'
base_name_only_sub = (r'', re.compile(r'(?<!:[.:])[\w,.]+(?:\.(?!:\[))'))

# matches the type hint equivalent to Optional[Type]:
#   Union[TYPE, NoneType], where TYPE is an arbitrary type
optional_hint_sub = (r'Opt\1', re.compile(r'Union\[(?P<paramType>[\w\d,|\[\] ]+), NoneType\]'))

# matches the " -> " of a return type hint:
#   def func(param: TYPE) -> TYPE:
return_hint_sub = (r': ', re.compile(r' -> '))

# Matches the "self, " param in a method definition:
#   def mthd(self, param: TYPE) -> TYPE:
self_sub = (r'', re.compile(r'self(?:, )?'))

# A list of substitutions to perform on the function's signature
signature_substitions = [
	base_name_only_sub,
	optional_hint_sub,
	return_hint_sub,
	self_sub,
	('ListDictMsg', re.compile(r'Dict\[str, List\[Dict\]\]')),
	(r'OperationParam', re.compile(r'Dict\[str, Union\[float, FrequencyRange\]\]')),
	(r'GrantRequest', re.compile(r'Dict\[str, Union\[str, OperationParam, MeasReport\]\]')),
	(r'HeartbeatRequest', re.compile(r'Dict\[str, Union\[str, bool, MeasReport\]\]')),
]


def mk_sig_sub_from_alias(
	alias: typing._GenericAlias,
	replace_with: str,
	mk_prelim_subs: bool = True,
	prelim_sub_map: List[Tuple] = signature_substitions[:4]
) -> Tuple[str, re.Pattern]:
	"""
	Creates a substitution tuple (a string with which to replace matches from the re.Pattern object it comes with, the re.Pattern to use to match).
	:param alias: a type alias, which is defined using the following syntax: alias = Type
	:param replace_with: The string with which to replace matches from the created re.Pattern object. You likely want this to be the name of the alias.
	:returns: a tuple with two elements- a string and a compiled regex object.
	"""
	alias_sub = []

	# make <replace_with> the first element of the returned tuple
	alias_sub.append(replace_with)

	alias_str = str(alias)

	# Use the substituion tuples in prelim_sub_map to replace type hints
	# 	appearing as a substring within alias_str with their equivalent type aliases
	for t in list(prelim_sub_map):
		alias_str = t[1].sub(t[0], alias_str)

	# Create a re.Pattern object from the type alias' definition
	# 	escape all instances of square braces
	re_pat_str = alias_str.replace('[', '\[').replace(']', '\]')
	# 	compile resulting str into a regex Pattern
	re_pat = eval(f"re.compile(r'{re_pat_str}')")

	# make the regex pattern the second element of the returned tuple
	alias_sub.append(re_pat)

	return tuple(alias_sub)


def mk_module_alias_substitions(
	module: Union[ModuleType, str],
	reload_module: bool = False,
	# prelim_sub_map: List[Tuple[str, re.Pattern]] = signature_substitions[:4]
	prelim_sub_map: List[Tuple[str, re.Pattern]] = signature_substitions
) -> List[Tuple[str, re.Pattern]]:
	"""
	Returns a list of substitution tuples (a string with which to replace matches from the re.Pattern object it comes with, the re.Pattern to use to match), with one elem per type alias in the given module.
	:param module: either a module object on which to operate, or the name of (path to) a module file on which to temporarily import
	:param reload_module: If True (False by default), then the function will reload the given module (which must have been previously imported) to use any changes to the module since it was imported.
	"""
	mod = _accept_module_or_str(module, reload_module)
	aliases = get_module_type_aliases(mod, False)

	new_subs = list(copy.deepcopy(prelim_sub_map))

	for k, v in aliases.items():
		# skip the alias if it's not user-defined
		if getattr(v, '_special', False):
			continue

		new_subs.append(
			mk_sig_sub_from_alias(v, k, prelim_sub_map=new_subs)
		)

	return new_subs


def module_types(module):
	return [t[0] for t in _filterGlobalsListByType(obj=module, desiredType=typing.Type)]


# @typing.no_type_check
def format_signature(
	func: typing.Callable,
	type_aliases: Optional[List[Tuple]] = signature_substitions,
	include_visibility_indicator: bool = True
) -> str:
	"""
	Gets the given function's signature and returns a str signature suitable for use in a UML class diagram.
	:param func: the function for which to return its formatted signature
	:param type_aliases: A dictionary mapping type aliases (as keys) to equivalent types/type hints. Whenever the type hint is encountered, it is replaced by the type alias.
	:param include_visibility_indicator: If True (default), then prepend '+ ' or '- ' to the formatted signature to indicate that the function is "public" or "private" (in the case of a sunder or dunder function), respectively.
	"""
	sig_str = str(get_signature(func))

	for t in type_aliases:
		sig_str = t[1].sub(t[0], sig_str)

	if include_visibility_indicator:
		indicator = '-' if func.__name__.startswith('_') else '+'
		return f"{indicator} {func.__name__}{sig_str}"
	else:
		return f"{func.__name__}{sig_str}"


def _temporary_module_operation(
	func: typing.types.FunctionType,
	module_name: str,
	module_package: Optional[str] = None
):
	"""
	Perform the 'func' operation on the given module without adding the module to the globals dict.
	Note that this function does not reload modules or invalidate the module cache, so if you want
	to use new modifications to the given module after already having imported it, you need to first
	use importlib.reload() on the module.
	:param func: A function with a single argument for the module on which to operate
	:param module_name: The name of the module on which to operate
	:param module_package: The 'package' field in a f"from {package} import {module}" relative import statement
	"""
	module = importlib.import_module(module_name, module_package)

	return func(module)


def get_module_method_sigs(
	module: Union[ModuleType, str],
	reload_module: bool = False,
	type_aliases: Optional[List[Tuple]] = signature_substitions,
	include_visibility_indicator: bool = True
) -> Dict:
	"""
	For each class in the given module, create a dictionary key-value pair with the key being the name of the class, and the value being a dictionary of the methods for that class, with the key being the name of the method, and the value being the method's signature.
	:param module: either a module object on which to operate, or the name of (path to) a module file on which to temporarily import
	:param reload_module: If True (False by default), then the function will reload the given module (which must have been previously imported) to use any changes to the module since it was imported.
	:param type_aliases: A dictionary mapping type aliases (as keys) to equivalent types/type hints. Whenever the type hint is encountered, it is replaced by the type alias.
	:param include_visibility_indicator: If True (default), then prepend '+ ' or '- ' to the formatted signature to indicate that the function is "public" or "private" (in the case of a sunder or dunder function), respectively.
	"""
	mod = _accept_module_or_str(module, reload_module)

	mod_methods = get_module_classes_methods(mod, reload_module=False)

	mod_sigs = dict.fromkeys(mod_methods.keys())

	subs = copy.deepcopy(type_aliases)
	subs.extend(mk_module_alias_substitions(mod, reload_module=False))

	for k in mod_methods.keys():
		mod_sigs[k] = dict.fromkeys(mod_methods[k])

	for cls, mthds in mod_methods.items():
		for mthd in mthds:
			fsig_arg = getattr(getattr(mod, f"{cls}"), f"{mthd}")
			mod_sigs[cls].update({ f'{mthd}': format_signature(fsig_arg, subs) })

	return mod_sigs

