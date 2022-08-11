#!/bin/python3
import unittest, sys, re, os, inspect, logging
from functools import wraps
from typing import List, Optional, Union, Tuple, Callable
from types import ModuleType
from get_module_classes_methods import _accept_module_or_str, get_module_classes


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
	print(tsuite)
	
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
) -> Tuple[List, ...]:
	tests = get_all_testnames_from_testdir(path, prefix, suffix, qualified_prefix)
	
	passed = []
	failed = []
	
	for test in tests:
		try:
			tr.run_tests_by_name(test)
			passed.append(test)
		except Exception as exc:
			failed.append(test)
			# errors.append((test, exc))
	
	return passed, failed	

if __name__ == "__main__":
	print(list(enumerate(sys.argv)))
	print(type(sys.argv[1]))
	tr = run_tests_by_name(sys.argv[1])
	print(tr)
