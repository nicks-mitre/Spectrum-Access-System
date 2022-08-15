#!/bin/python3
import unittest, sys, re, os, inspect, logging, importlib
from functools import wraps
from typing import List, Optional, Union, Tuple, Callable, Dict, Type
from types import ModuleType
from get_module_classes_methods import _accept_module_or_str, _filterGlobalsListByType, get_module_classes


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

	filt_classes = _filterGlobalsListByType(obj=mod, desiredType=Type)
	classes = [t[0] for t in filt_classes]
	if sort:
		return sorted(classes)
	else:
		return classes


def temp_set_logger_level(
	level: int = logging.ERROR,
	logger: logging.Logger = logging.getLogger()
) -> Callable:
	"""
	A decorator to temporarily set the logging level of the given logger to 'level', call a function, and then reset the level back to its previous value.
	"""

	def deco_temp_disable_logging(func: Callable):
		@wraps(func)
		def wrapper_temp_disable_logging(*args, **kwargs):
			# store the current level of logger
			log_lvl = logger.level

			print(f"curr_level: {logger.level}")
			# disable the logger for level 'level' and below
			logger.setLevel(level)
			print(f"set_level: {logger.level}")
			# call func
			res = func(*args, **kwargs)
			# restore logger to previous level
			logger.setLevel(log_lvl)
			print(f"restored_lvl: {logger.level}")
			return res

		return wrapper_temp_disable_logging

	return deco_temp_disable_logging


def run_tests_by_name(test: str) -> unittest.TextTestRunner.resultclass:
	"""
	Run the given test(s) specified by the given name.

	"The name may resolve either to a module, a test case class, a test method within a test case class, or a callable object which returns a TestCase or TestSuite instance." (unittest.loadTestsFromName docstring)
	"""
	tloader = unittest.TestLoader()

	tsuite = tloader.loadTestsFromName(test)
	# print(tsuite)

	ttr = unittest.TextTestRunner()

	return ttr.run(tsuite)


def get_testcase_modules(
	path: str,
	prefix: str = "WINNF",
	suffix: str = "_testcase.py",
	prepend_path: bool = True
) -> List[str]:
	"""
	Returns a list of modules beginning with the given prefix and ending with the given suffix in the given 'path' directory.
	"""
	files = os.listdir(path)
	if prefix and suffix:
		files = [i for i in files if i.startswith(prefix) and i.endswith(suffix)]
	elif prefix:
		files = [i for i in files if i.startswith(prefix)]
	elif suffix:
		files = [i for i in files if i.endswith(suffix)]

	# get the default path separator in the current environment
	sep = os.path.sep
	if prepend_path:
		# if path doesn't end with a slash, then append one so that os.path.dirname works properly
		if not path.endswith('/'):
			path += '/'
		# take the directory part of 'path' and replace all path separators with a period
		# so the resulting modules can be directly imported
		path_prefix = os.path.dirname(path).replace(sep, '.')
		files = [f"{path_prefix}.{i}" for i in files]
	return files


def modname_from_test_mthd(mthd_name: str) -> str:
	"""
	Returns the name of the module in which the given testmethod is found
	"""
	test_rgx = re.compile(r'^test_')
	modname_rgx = re.compile(r'_\d.*$')

	base = test_rgx.sub('', modname_rgx.sub('', mthd_name))
	if not base.endswith('_testcase'):
		base += '_testcase'
	return base


def get_testcase_classes_from_module(
	module: Union[str, ModuleType],
	cls_suffix: str = "Testcase",
	cls_prefix: Optional[str] = None
) -> List[str]:
	"""
	Returns a list of testcase class names in the given module
	:param mod: either a module object on which to operate, or the name of (path to) a module file on which to temporarily import
	"""

	mod = _accept_module_or_str(module)

	all_classes = get_module_classes(mod, reload_module=False)

	# filter out imported classes
	path = mod.__file__

	classes = []
	for str_cls in all_classes:
		# print(f"mname: {mod.__name__}; cls: {str_cls}")
		cls = getattr(mod, str_cls)
		# inspect.getsourcefile(OBJ) errors if OBJ is a builtin
		# so, we check if the class' name is in the __builtins__ module
		# if (
		# hasattr(__builtins__, str_cls) or
		# str_cls in sys.builtin_module_names
		# ):
		# print(f"{str_cls = :}")
		# continue
		try:
			if inspect.getsourcefile(cls) == path:
				classes.append(str_cls)
		except TypeError:
			continue

	return [i for i in classes if i.endswith("Testcase")]


def get_fully_qual_testnames_from_mod(
	module: Union[ModuleType, str],
	prefix: Optional[str] = None
) -> List[str]:
	"""
	Returns a list of testmethod names within the given module in the following (fully qualified) format:
	f"{prefix}.{module_name}.{testcase_class_name}.{test_method_name}"
	"""
	mod = _accept_module_or_str(module)
	test_classes = get_testcase_classes_from_module(mod)

	fq_testmethods = []

	tloader = unittest.TestLoader()

	for cls in test_classes:
		for test_name in tloader.getTestCaseNames(getattr(mod, cls)):
			if prefix:
				fq_testmethods.append(f"{prefix}.{mod.__name__}.{cls}.{test_name}")
			else:
				fq_testmethods.append(f"{mod.__name__}.{cls}.{test_name}")

	return fq_testmethods


def get_all_testnames_from_testdir(
	path: str,
	prefix: str = "WINNF",
	suffix: str = "_testcase.py",
	qualified_prefix: Optional[str] = 'testcases'
) -> List[str]:
	"""
	Returns a list containing the fully-qualified test method names for each testcase class witin each test module in the given directory 'path'. The names are given in the following (fully qualified) format:
	f"{prefix}.{module_name}.{testcase_class_name}.{test_method_name}"
	"""
	test_method_names = []

	t_modules = get_testcase_modules(path, prefix, suffix)
	for mod in t_modules:
		test_method_names.extend(
			get_fully_qual_testnames_from_mod(mod, qualified_prefix)
		)

	return test_method_names


def record_all_test_res_from_testdir(
	path: str,
	prefix: str = "WINNF",
	suffix: str = "_testcase.py",
	qualified_prefix: Optional[str] = None
) -> Tuple[Dict[str, str], ...]:
	tests = get_all_testnames_from_testdir(path, prefix, suffix, qualified_prefix)

	# results = {"passed": [], "failed": []}
	results = { }
	# names = {"passed": [], "failed": []}
	text_results = { }

	for test in tests:
		res = run_tests_by_name(test)

		if res.wasSuccessful():
			results[test] = res
			text_results[test] = "Passed"
		else:
			results[test] = res
			text_results[test] = "Failed"

	return results, text_results


if __name__ == "__main__":
	print(list(enumerate(sys.argv)))
	print(type(sys.argv[1]))
	tr = run_tests_by_name(sys.argv[1])
	print(tr)
