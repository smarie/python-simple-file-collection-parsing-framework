from io import TextIOBase
from pprint import pprint
from typing import List, Set, Dict
from unittest import TestCase

from sficopaf import RootParser, FolderAndFilesStructureError, FileMappingConfiguration
from sficopaf import get_simple_object_parser


class SimpleObjectsTest(TestCase):

    def test_simple_object(self):

        # First define the function that we want to test (not useful, but just to show a complete story in the readme...)
        def exec_op(x: float, y: float, op: str) -> float:
            if op is '+':
                return x + y
            elif op is '-':
                return x - y
            else:
                raise ValueError('Unsupported operation : \'' + op + '\'')


        # Then define the simple class representing your test case
        class ExecOpTest(object):

            def __init__(self, x: float, y: float, op: str, expected_result: float):
                self.x = x
                self.y = y
                self.op = op
                self.expected_result = expected_result

        # create the parser and parse a single file
        simple_parser = get_simple_object_parser(ExecOpTest)

        t = simple_parser.get_all_known_parsing_chains()
        pprint(t)
        e = simple_parser.parse_item('./test_data/demo_simple/test_diff_1', ExecOpTest)
        print(e.x)
        print(e.y)
        print(e.op)
        print(e.expected_result)



    def test_simple_object_with_contract(self):

        from classtools_autocode import autoprops, autoargs
        from contracts import contract, new_contract

        # custom contract needed in the class
        new_contract('allowed_op', lambda x: x in {'+', '-'})

        @autoprops
        class ExecOpTest(object):
            @autoargs
            @contract(x='int|float', y='int|float', op='str,allowed_op', expected_result='int|float')
            def __init__(self, x: float, y: float, op: str, expected_result: float):
                pass

        # Test
        ExecOpTest(0,0,'+',2)


class MainTest(TestCase):

    def setUp(self):
        self.root_parser, self.main_type = self._create_root_parser()

    def test_root_parser(self):
        pprint(self.root_parser.get_parsers_copy())
        return

    def test_single_item_folders(self):
        f = self.root_parser.parse_item('./test_data/with_folders/item1', self.main_type)
        pprint(f)
        return

    def test_single_item_no_folders(self):

        config = FileMappingConfiguration(flat_mode=True)
        with self.assertRaises(FolderAndFilesStructureError):
            f = self.root_parser.parse_item('./test_data/without_folders/item1', List[self.main_type], file_mapping_conf=config)

        f = self.root_parser.parse_item('./test_data/without_folders/item1', self.main_type, file_mapping_conf=config)
        pprint(f)
        return

    def test_single_item_that_is_a_list(self):
        f = self.root_parser.parse_item('./test_data/with_folders', List[self.main_type])
        pprint(f)
        self.assertEqual(len(f), 3)
        return

    def test_with_folders_list(self):
        l = self.root_parser.parse_collection('./test_data/with_folders', List[self.main_type])
        pprint(l)
        self.assertEqual(len(l), 3)
        return

    def test_with_folders_set(self):
        s = self.root_parser.parse_collection('./test_data/with_folders', Set[self.main_type])
        pprint(s)
        self.assertEqual(len(s), 3)
        return

    def test_with_folders_dict(self):
        d = self.root_parser.parse_collection('./test_data/with_folders', self.main_type)
        pprint(d)
        self.assertEqual(len(d), 3)
        return

    def test_no_folders(self):

        config = FileMappingConfiguration(flat_mode=True)
        d = self.root_parser.parse_collection('./test_data/without_folders', self.main_type, file_mapping_conf=config)
        pprint(d)
        self.assertEqual(len(d), 3)
        return


    def _create_root_parser(self):

        # This framework allows users to parse (collections of) objects from files. Each object is a dictionary with
        # user-defined fields. Each field is mapped to a file, or a collection of files in a folder.

        # Step 1: define the applicative data model.
        # ------------------------------------------
        # a) define the *basic* types of the objects you want to read from files.
        # Each of these object types should be readable from *one* (and only one) file.
        #
        # -- Sometimes you will feel the need to use a class of your own, that probably already exists in your program:
        class OneLiner(object):
            """
            A very simple type wrapping some text contents.
            """
            def __init__(self, contents:str):
                self.contents = contents

            def __str__(self):
                """ readable representations """
                return self.contents

            def __repr__(self):
                """ unambiguous representation """
                return self.contents

        # -- In many cases, you will feel the need to wrap an existing object, that a parsing library already returns
        from configparser import ConfigParser

        class Config(ConfigParser):
            """
            A Config object is a ConfigParser object with only one 'main' section
            """
            def __init__(self, config: ConfigParser):
                super(Config, self).__init__()
                self.__wrapped_impl = config

                # here you may wish to perform additional checks on the wrapped object,
                # for example here we check that the config only has one section named 'main'
                if 'main' not in config.sections():
                    raise Exception('Wrong Config configuration : mandatory main section is missing')
                if len(config.sections()) != 1:
                    raise Exception('Wrong Config configuration : there should only be one main section')


            # Delegate all calls to the implementation:
            def __getattr__(self, name):
                return getattr(self.__wrapped_impl, name)

        # OneLiner = type('OneLiner', (), {}) # NewType('ParamDict', Dict[str, str])


        # b) Define the main schema of the dictionary object that you want to parse.
        #
        # , that spans across several files. This is the object you
        # *really* want as the outcome of the parsing step. For example it might represent a test case.
        class MainFooBarItem(object):
            """
            The main class of objects that we want to parse. The signature of its constructor will be used to infer
            the parsers to use and to check which attributes are optional or not.
            """
            def __init__(self, input_simple: OneLiner, expected_out: Config, expected_perf: Config = None):
                self.input_simple = input_simple
                self.expected_out = expected_out
                self.expected_perf = expected_perf

            def get_as_dict(self):
                return {'input_simple': self.input_simple, 'expected_out': self.expected_out, 'expected_perf' : self.expected_perf}

            def __str__(self):
                return self.get_as_dict().__str__()

            def __repr__(self):
                return self.get_as_dict().__repr__()


        #todo being able to return all items in a collection that have no error, while ignoring the others


        # Step 2: for each basic type, define at least one parsing function, that has one mandatory input
        # (file_object: TextIOBase, stream opened from the file by the framework) and that returns an object of the
        # expected type. Note that the stream will be closed automatically by the framework
        #
        def read_oneliner_from_txt_file_stream(file_object: TextIOBase) -> OneLiner:
            """
            Helper method to read a txt file and return its content as a OneLiner object.
            :param file_object: stream opened from the file by the framework, and closed automatically after parsing
            :return: a new object created from the file.
            """

            # read the file - or at least the first row
            first_row = file_object.readline()
            # no need to close, that will be done by caller

            return OneLiner(first_row)

        def read_config_from_config_file_stream(file_object: TextIOBase) -> Config:
            """
            Helper method to read a txt file and return its content as a Config object.
            :param file_object: stream opened from the file by the framework, and closed automatically after parsing
            :return: a new object created from the file.
            """
            import configparser
            config = configparser.ConfigParser()
            config.read_file(file_object)

            return Config(config)

        # Step 3: register all basic types, along with at least one parsing function. The framework allows to register
        # several file extensions for each basic type - each file extension being associated with a unique parsing
        # function. For example an object might be available as a .cfg, a .txt or a .csv three parsing functions would
        # then be registered. Note that you may register the same function twice if it is able to handle several file
        # extensions.
        #
        parsers = {
            OneLiner: {
                '.txt': read_oneliner_from_txt_file_stream
            },
            Config: {
                '.cfg': read_config_from_config_file_stream,
                '.txt': read_config_from_config_file_stream
            }
        }

        # create root parser
        root_parser = RootParser()
        root_parser.register_parsers(parsers)

        return root_parser, MainFooBarItem



class TestDemo(TestCase):

    def test_demo(self):
        # In this demonstrative example, we will parse 'test cases' for an imaginary function that performs operations :
        # op_function(a:int, b:int, operation:str = '+') -> int
        #
        # Each of our 'test case' items will be made of several things:
        # * mandatory input data (here, a and b)
        # * optional configuration (here, operation)
        # * mandatory expected result (here, the output)

        # We would like these things stored in four separate files. Typically the reason is that you will want to
        # separate the various formats that you wish to use: csv, xml, json...
        # So our data folder structure looks like this:

        # test_cases
        # ├── case1
        # │   ├── input_a.txt
        # │   ├── input_b.txt
        # │   └── output.txt
        # ├── case2
        # │   ├── input_a.txt
        # │   ├── input_b.txt
        # │   ├── options.txt
        # │   └── output.txt
        # └── case3
        # ├── input_a.txt
        # ├── input_b.txt
        # ├── options.cfg
        # └── output.txt

        # Note that the configuration file is optional. Here, only `case2` and `case3` will have a non-default configuration.
        # You may also have noticed that the configuration file is present with two different extensions :
        # `.txt` (in case2) and `.cfg` (in case3). This framework allows to register several file extensions for the
        # same type of object to parse. Each extension may have its own parser function.

        # First import the package and create a root parser.

        import sficopaf as sf
        root_parser = sf.RootParser()

        # Then register a parser function for all items that will be represented as **single** files.
        # * In this example, all inputs and outputs are `int` so we create a first function to parse an int from a text file:

        #from io import TextIOBase
        def parse_int_file(file_object: TextIOBase) -> int:
            integer_str = file_object.readline()
            return int(integer_str)

        root_parser.register_unitary_parser(int, '.txt', parse_int_file)

        # Note that the parsing framework automatically opens and closes the file for you, even in case of exception.

        # We also need to be able to read an `configuration`, that is a `Dict[str, str]` in our case. We propose two formats:
        # * one `.txt` format where the first row will directly contain the value for the operation, and
        # * one `.cfg` format where the configuration will be available in the configparser format.

        #from typing import Dict
        class OpConfig(dict):
            """
            An OpConfig object is a Dict[str, str] object
            """
            def __init__(self, config: Dict[str, str]):
                super(OpConfig, self).__init__()
                self.__wrapped_impl = config

                # here you may wish to perform additional checks on the wrapped object
                unrecognized = set(config.keys()) - set('operation')
                if len(unrecognized) > 0:
                    raise ValueError('Unrecognized options : ' + str(unrecognized))

            # Delegate all calls to the implementation:
            def __getattr__(self, name):
                return getattr(self.__wrapped_impl, name)

        def parse_configuration_txt_file(file_object: TextIOBase) -> Dict[str, str]:
            return {'operation': file_object.readline()}

        def parse_configuration_cfg_file(file_object: TextIOBase) -> Dict[str, str]:
            import configparser
            config = configparser.ConfigParser()
            config.read_file(file_object)
            return dict(config['main'].items())

        root_parser.register_unitary_parser(OpConfig, '.txt', parse_configuration_txt_file)
        root_parser.register_unitary_parser(OpConfig, '.cfg', parse_configuration_cfg_file)


        # Finally we define the 'test case' objects
        class OpTestCase(object):
            def __init__(self, input_a: int, input_b: int, output: int, options: OpConfig = None):
                self.input_a, self.input_b, self.output = input_a, input_b, output
                if options is None:
                    self.op = '+'
                else:
                    self.op = options['operation']

            def __str__(self):
                return self.__repr__()

            def __repr__(self):
                return str(self.input_a) + ' ' + self.op + ' ' + str(self.input_b) + ' =? ' + str(self.output)

        # And we parse a collection of these
        results = root_parser.parse_collection('./test_data/demo', OpTestCase)
        pprint(results)

        conf = FileMappingConfiguration(flat_mode=True, sep_for_flat='--')
        results = root_parser.parse_collection('./test_data/demo_flat', OpTestCase, file_mapping_conf=conf)
        pprint(results)

        class OpTestCaseColl(object):
            def __init__(self, input_a: int, input_b: int, output: int,
                         input_c: Dict[str, List[int]] = None, options: OpConfig = None):
                self.input_a, self.input_b, self.output = input_a, input_b, output
                if options is None:
                    self.op = '+'
                else:
                    self.op = options['operation']
                self.input_c = input_c or None

                def __str__(self):
                    return self.__repr__()

                def __repr__(self):
                    return str(self.input_a) + ' ' + self.op + ' ' + str(self.input_b) + ' =? ' + str(
                        self.output) + ' ' + str(self.input_c)


        results = root_parser.parse_collection('./test_data/demo_flat_coll', OpTestCaseColl, file_mapping_conf=conf)
        pprint(results['case3'].input_c)

        results = root_parser.parse_collection('./test_data/demo_coll', OpTestCaseColl)
        pprint(results['case3'].input_c)