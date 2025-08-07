# CntxtPY.py - Python codebase analyzer that generates comprehensive knowledge graphs optimized for LLM context windows

import os
import sys
import json
import networkx as nx
from networkx.readwrite import json_graph
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
import logging
from datetime import datetime

# Import regex modules
try:
    from regex_components.ConfigFileParser import ConfigFileParser
    from regex_components.DependencyMapper import DependencyMapper
    from regex_components.CodeIdentifierExtractor import CodeIdentifierExtractor, FunctionInfo, Parameter
    from regex_components.CommentProcessor import CommentProcessor
    from regex_components.DocumentationAnalyzer import DocumentationAnalyzer
    from regex_components.BuildConfigExtractor import BuildConfigExtractor
    from regex_components.LoggingAnalyzer import LoggingAnalyzer
    from regex_components.VersionAnalyzer import VersionAnalyzer
    from regex_components.FileTypeProcessor import FileTypeProcessor
    from regex_components.IntegrationMapper import IntegrationMapper
    from regex_components.LocalizationProcessor import LocalizationProcessor
    from regex_components.CommentProcessor import CommentInfo, CommentType
except ImportError as e:
    print(f"Error importing regex components: {str(e)}")
    print("Make sure all component files are in the 'regex_components' directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class PythonCodeKnowledgeGraph:
    def __init__(self, directory: str):
        """Initialize the knowledge graph generator."""
        self.directory = directory
        self.graph = nx.DiGraph()
        self.files_processed = 0
        self.total_files = 0
        self.dirs_processed = 0
        self.analyzed_files = set()
        self.module_map = {}

        # Initialize statistics
        self.stats = {
            'total_classes': 0,
            'total_functions': 0,
            'total_modules': set(),
            'total_imports': 0,
            'total_dependencies': set(),
            'total_annotations': set(),
            'total_logging_statements': 0,
            'files_with_errors': 0,
            'total_comments': 0,
            'total_configs': 0,
            'total_integrations': 0,
            'total_localizations': 0,
            'total_build_scripts': 0,
            'total_version_constraints': 0,
            'total_variables': 0,
            'total_constants': 0
        }

        # Initialize processors and ignored paths
        self._init_processors()
        self._init_ignored_paths()

    def _init_processors(self):
        """Initialize all component processors."""
        try:
            # Pass the directory when initializing the VersionAnalyzer
            self.version_analyzer = VersionAnalyzer(directory=self.directory)
            self.config_parser = ConfigFileParser()
            self.dependency_mapper = DependencyMapper()
            self.code_extractor = CodeIdentifierExtractor()
            self.comment_processor = CommentProcessor()
            self.doc_analyzer = DocumentationAnalyzer()
            self.build_extractor = BuildConfigExtractor()
            self.log_analyzer = LoggingAnalyzer()
            self.file_processor = FileTypeProcessor()
            self.integration_mapper = IntegrationMapper()
            self.localization_processor = LocalizationProcessor()
        except Exception as e:
            logging.error(f"Error initializing processors: {str(e)}")
            raise

    def _init_ignored_paths(self):
        """Initialize sets of ignored directories and files."""
        self.ignored_directories = {
            '__pycache__', '.git', '.idea', '.vscode', '.venv', 'env', 'venv',
            '.mypy_cache', '.pytest_cache', '.eggs', 'build', 'dist', 'node_modules',
            '.tox', '.coverage', '.svn', '.hg'
        }

        self.ignored_files = {
            '.gitignore', '.DS_Store', 'Thumbs.db', '.env', '.env.example'
        }

    def _add_dependency_node(self, build_node: str, dep_info: Dict[str, str]):
        """Add a dependency node to the graph."""
        dep_id = f"{dep_info['name']}=={dep_info.get('version', '')}"
        dep_node = f"Dependency: {dep_id}"
        if not self.graph.has_node(dep_node):
            self.graph.add_node(
                dep_node,
                type="dependency",
                name=dep_info['name'],
                version=dep_info.get('version', ''),
                id=dep_node
            )
            self.stats['total_dependencies'].add(dep_id)
        self.graph.add_edge(build_node, dep_node, relation="DEPENDS_ON")

    def analyze_codebase(self):
        """Analyze the Python codebase and build the knowledge graph."""
        logging.info("Starting codebase analysis...")

        # Count files first
        self._count_files()

        # Process the codebase
        self._process_codebase()

        logging.info(f"Completed analysis of {self.files_processed} files")
        if self.stats['files_with_errors'] > 0:
            logging.warning(f"Encountered errors in {self.stats['files_with_errors']} files")

    def _count_files(self):
        """Count total files to be processed."""
        for root, dirs, files in os.walk(self.directory):
            dirs[:] = [d for d in dirs if d not in self.ignored_directories]

            if not any(ignored in root.split(os.sep) for ignored in self.ignored_directories):
                self.total_files += sum(
                    1 for f in files
                    if f.endswith(".py") and f not in self.ignored_files
                )
                # Include build files
                self.total_files += sum(
                    1 for f in files
                    if f in {"setup.py", "requirements.txt", "Pipfile", "pyproject.toml"} and f not in self.ignored_files
                )
                # Include config files
                self.total_files += sum(
                    1 for f in files
                    if f.endswith((".ini", ".env", ".cfg", ".yaml", ".yml", ".json")) and f not in self.ignored_files
                )
                # Include localization files
                self.total_files += sum(
                    1 for f in files
                    if f.endswith((".po", ".mo")) and f not in self.ignored_files
                )
                # Include README and documentation files
                self.total_files += sum(
                    1 for f in files
                    if f.lower() in {"readme.md", "readme.rst", "api.md", "docs.md"} and f not in self.ignored_files
                )

        logging.info(f"Found {self.total_files} files to process")

    def _process_codebase(self):
        """Process all files in the codebase."""
        for root, dirs, files in os.walk(self.directory):
            dirs[:] = [d for d in dirs if d not in self.ignored_directories]

            if any(ignored in root.split(os.sep) for ignored in self.ignored_directories):
                continue

            rel_path = os.path.relpath(root, self.directory)
            self.dirs_processed += 1
            logging.debug(f"Processing directory [{self.dirs_processed}]: {rel_path}")

            for file in files:
                if file in self.ignored_files:
                    continue

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.directory)

                if file.endswith(".py"):
                    self._process_python_file(file_path)
                elif file in {"setup.py", "requirements.txt", "Pipfile", "pyproject.toml"}:
                    self._process_build_file(file_path)
                elif file.endswith((".ini", ".env", ".cfg", ".yaml", ".yml", ".json")):
                    self._process_config_file(file_path)
                elif file.endswith((".po", ".mo")):
                    self._process_localization_file(file_path)
                elif file.lower() in {"readme.md", "readme.rst", "api.md", "docs.md"}:
                    self._process_documentation_file(file_path)
                else:
                    self._process_generic_file(file_path)

    def _process_python_file(self, file_path: str):
        """Process a single Python file."""
        if file_path in self.analyzed_files:
            return

        try:
            self.files_processed += 1
            relative_path = os.path.relpath(file_path, self.directory)
            logging.debug(f"Processing file [{self.files_processed}/{self.total_files}]: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Add file node
            file_node = f"File: {relative_path}"
            self.analyzed_files.add(file_path)
            self.graph.add_node(file_node, type="file", path=relative_path, encoding="UTF-8", fileType="SOURCE_CODE")

            # Process file contents
            self._process_file_contents(file_node, content, file_path)

        except Exception as e:
            logging.error(f"Error processing {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def _process_file_contents(self, file_node: str, content: str, file_path: str):
        """Process the contents of a Python file using all analyzers."""
        try:
            # Process imports
            imports = self.dependency_mapper.extract_imports(content)
            for import_name in imports:
                self._add_import_node(file_node, import_name)

            # Process classes
            classes = self.code_extractor.extract_classes(content)
            for class_info in classes:
                class_name = class_info.name
                self._add_class_node(file_node, class_name)

                # Add class annotations (decorators)
                for annotation in class_info.decorators:
                    self._add_annotation_node(file_node, annotation)

                # Process methods within the class
                for method in class_info.methods:
                    self._add_method_node(class_name, method)
                    # Add method annotations (decorators)
                    for annotation in method.decorators:
                        self._add_annotation_node(file_node, annotation)

            # Process functions
            functions = self.code_extractor.extract_functions(content)
            for function_info in functions:
                self._add_function_node(file_node, function_info)
                # Add function annotations (decorators)
                for annotation in function_info.decorators:
                    self._add_annotation_node(file_node, annotation)

            # Process variables and constants
            variables = self.code_extractor.extract_variables(content)
            for variable_info in variables:
                self._add_variable_node(file_node, variable_info)

            # Process comments and documentation
            comments = self.comment_processor.extract_comments(content)
            for comment in comments:
                self._add_comment_node(file_node, comment)

            # Process logging statements
            logging_statements = self.log_analyzer.extract_logs(content)
            for log in logging_statements:
                self._add_log_statement_node(file_node, log)

            # Process integrations
            integrations = self.integration_mapper.extract_integrations(content)
            for integration in integrations:
                self._add_integration_node(file_node, integration)

            # Process version constraints
            version_info = self.version_analyzer.extract_version_constraints(content)
            if version_info:
                self._add_version_info(file_node, version_info)

            # Process localization usage
            localizations = self.localization_processor.extract_localizations(content)
            for localization in localizations:
                self._add_localization_usage_node(file_node, localization)

        except Exception as e:
            logging.error(f"Error in _process_file_contents for {file_node}: {str(e)}")
            raise

    def _add_import_node(self, file_node: str, import_name: str):
        """Add an import node to the graph."""
        import_node = f"Import: {import_name}"
        if not self.graph.has_node(import_node):
            self.graph.add_node(import_node, type="import", name=import_name, id=import_node)
            self.stats['total_imports'] += 1
            logging.debug(f"Import added: {import_name}, Total imports: {self.stats['total_imports']}")
        self.graph.add_edge(file_node, import_node, relation="IMPORTS")
        logging.debug(f"Edge added: {file_node} -> {import_node} with relation IMPORTS")

    def _add_class_node(self, file_node: str, class_name: str):
        """Add a class node to the graph."""
        class_node = f"Class: {class_name}"
        if not self.graph.has_node(class_node):
            self.graph.add_node(class_node, type="class", name=class_name, id=class_node)
            self.stats['total_classes'] += 1
            logging.debug(f"Class node added: {class_node}, Total classes: {self.stats['total_classes']}")
        else:
            logging.debug(f"Class node already exists: {class_node}")

        self.graph.add_edge(file_node, class_node, relation="DEFINES")
        logging.debug(f"Edge added: {file_node} -> {class_node} with relation DEFINES")

    def _add_method_node(self, class_name: str, method_info: FunctionInfo):
        """
        Add a method node to the graph.

        Improvements:
        - Ensures parameters and decorators are JSON-serializable.
        - Coerces sets to lists and converts enums or unknown objects to strings.
        - Handles default_value fallback if unserializable.
        """

        method_name = method_info.name
        method_node = f"Method: {method_name}"

        if not self.graph.has_node(method_node):
            # Safely convert parameters
            parameters = []
            for param in method_info.parameters:
                try:
                    default_val = param.default_value
                    json.dumps(default_val)  # Will raise if unserializable
                except Exception:
                    default_val = str(default_val)

                parameters.append({
                    'name': str(param.name),
                    'type': str(param.type_hint),
                    'default': default_val
                })

            # Safely convert decorators
            decorators_raw = method_info.decorators
            if isinstance(decorators_raw, (set, tuple)):
                decorators_raw = list(decorators_raw)

            decorators_clean = []
            for dec in decorators_raw:
                try:
                    decorators_clean.append(str(dec.value) if hasattr(dec, "value") else str(dec))
                except Exception:
                    decorators_clean.append(str(dec))

            self.graph.add_node(
                method_node,
                type="method",
                name=method_name,
                id=method_node,
                return_type=str(method_info.return_type),
                parameters=parameters,
                decorators=decorators_clean
            )
            self.stats['total_functions'] += 1
            logging.debug(f"Method node added: {method_node}, Total functions: {self.stats['total_functions']}")
        else:
            logging.debug(f"Method node already exists: {method_node}")

        # Link method to its class
        class_node = f"Class: {class_name}"
        if self.graph.has_node(class_node):
            self.graph.add_edge(class_node, method_node, relation="HAS_METHOD")
            logging.debug(f"Edge added: {class_node} -> {method_node} with relation HAS_METHOD")
        else:
            logging.warning(f"Class node {class_node} does not exist; cannot add method {method_name}")

    def _add_function_node(self, file_node: str, function_info: FunctionInfo):
        """
        Add a function node to the graph.

        Improvements:
        - Ensures parameters and decorators are JSON-serializable.
        - Coerces sets to lists and converts enums or unknown objects to strings.
        - Handles default_value fallback if unserializable.
        """

        function_name = function_info.name
        function_node = f"Function: {function_name}"

        if not self.graph.has_node(function_node):
            # Safely convert parameters to serializable format
            parameters = []
            for param in function_info.parameters:
                try:
                    default_val = param.default_value
                    # Ensure default_value is serializable
                    json.dumps(default_val)  # Will raise TypeError if not serializable
                except Exception:
                    default_val = str(default_val)  # Fallback to string

                parameters.append({
                    'name': str(param.name),
                    'type': str(param.type_hint),
                    'default': default_val
                })

            # Safely convert decorators (set, enum, etc → list of strings)
            decorators_raw = function_info.decorators
            if isinstance(decorators_raw, (set, tuple)):
                decorators_raw = list(decorators_raw)

            decorators_clean = []
            for dec in decorators_raw:
                try:
                    decorators_clean.append(str(dec.value) if hasattr(dec, "value") else str(dec))
                except Exception:
                    decorators_clean.append(str(dec))  # Defensive fallback

            # Add the sanitized function node
            self.graph.add_node(
                function_node,
                type="function",
                name=function_name,
                id=function_node,
                return_type=str(function_info.return_type),
                parameters=parameters,
                decorators=decorators_clean
            )
            self.stats['total_functions'] += 1
            logging.debug(f"Function node added: {function_node}, Total functions: {self.stats['total_functions']}")
        else:
            logging.debug(f"Function node already exists: {function_node}")

        # Link function to file
        self.graph.add_edge(file_node, function_node, relation="DEFINES")
        logging.debug(f"Edge added: {file_node} -> {function_node} with relation DEFINES")

    def _add_variable_node(self, file_node: str, variable_info: Dict[str, Any]):
        """
        Add a variable node to the graph.

        Enhancements:
        - Safely coerces variable 'value' and 'type_hint' to serializable strings.
        - Guards against malformed or unexpected input types.
        - Logs meaningful debug info and avoids crashes on invalid types.
        """
        import json

        variable_name = variable_info.get('name', '<unnamed>')
        variable_node = f"Variable: {variable_name}"

        # Coerce type_hint to string if needed
        raw_type = variable_info.get('type_hint', None)
        try:
            type_hint = str(raw_type)
        except Exception:
            type_hint = "<unreadable_type_hint>"

        # Coerce value to JSON-safe string or fallback
        raw_value = variable_info.get('value', None)
        try:
            json.dumps(raw_value)
            value = raw_value
        except Exception:
            value = str(raw_value) if raw_value is not None else None

        if not self.graph.has_node(variable_node):
            self.graph.add_node(
                variable_node,
                type="variable",
                name=variable_name,
                id=variable_node,
                value=value,
                type_hint=type_hint
            )
            self.stats['total_variables'] += 1
            logging.debug(f"Variable node added: {variable_node}, Total variables: {self.stats['total_variables']}")
        else:
            logging.debug(f"Variable node already exists: {variable_node}")

        # Link variable to file
        self.graph.add_edge(file_node, variable_node, relation="HAS_VARIABLE")
        logging.debug(f"Edge added: {file_node} -> {variable_node} with relation HAS_VARIABLE")

    def _add_annotation_node(self, file_node: str, annotation: Any):
        """
        Add an annotation (decorator) node to the graph.

        Enhancements:
        - Safely coerces decorator names to strings.
        - Handles AST nodes or malformed inputs.
        - Tracks unique decorators using a set.
        """
        # Fallback and type-safe conversion
        if annotation is None:
            annotation_str = "<None>"
        elif isinstance(annotation, str):
            annotation_str = annotation
        else:
            try:
                annotation_str = str(annotation)
            except Exception:
                annotation_str = "<unreadable_annotation>"

        annotation_node = f"Decorator: {annotation_str}"

        if not self.graph.has_node(annotation_node):
            self.graph.add_node(
                annotation_node,
                type="decorator",
                name=annotation_str,
                id=annotation_node
            )
            # Ensure stats field is initialized as a set
            if 'total_annotations' not in self.stats or not isinstance(self.stats['total_annotations'], set):
                self.stats['total_annotations'] = set()

            if annotation_str not in self.stats['total_annotations']:
                self.stats['total_annotations'].add(annotation_str)
                logging.debug(f"Decorator node added: {annotation_node}, Total unique decorators: {len(self.stats['total_annotations'])}")
        else:
            logging.debug(f"Decorator node already exists: {annotation_node}")

        self.graph.add_edge(file_node, annotation_node, relation="DECORATED_WITH")
        logging.debug(f"Edge added: {file_node} -> {annotation_node} with relation DECORATED_WITH")

    def _add_comment_node(self, file_node: str, comment: Any):
        """
        Safely adds a comment node to the graph.

        Defensive upgrades:
        - Coerces all fields with fallbacks.
        - Ensures stats field is valid.
        - Logs and skips corrupt comment objects.
        """
        try:
            # Coerce fields safely
            line_number = getattr(comment, 'line_number', -1)
            content = getattr(comment, 'content', '<no content>')
            comment_type = getattr(getattr(comment, 'type', None), 'value', 'unknown')
            associated_element = getattr(comment, 'associated_element', None)
            tags = getattr(comment, 'tags', []) or []

            try:
                comment_hash = hash(content)
            except Exception:
                comment_hash = hash("<bad content>")

            comment_id = f"Comment: {line_number}_{comment_hash}"
            comment_node = comment_id

            if not self.graph.has_node(comment_node):
                self.graph.add_node(
                    comment_node,
                    type="comment",
                    comment_type=comment_type,
                    content=content,
                    line_number=line_number,
                    associated_element=associated_element,
                    tags=tags,
                    id=comment_node
                )
                if 'total_comments' not in self.stats or not isinstance(self.stats['total_comments'], int):
                    self.stats['total_comments'] = 0
                self.stats['total_comments'] += 1
                logging.debug(f"Comment node added: {comment_node} (line {line_number})")

            self.graph.add_edge(file_node, comment_node, relation="HAS_COMMENT")
            logging.debug(f"Edge added: {file_node} -> {comment_node} with relation HAS_COMMENT")

        except Exception as e:
            logging.warning(f"Failed to add comment node: {e}")

    def _add_log_statement_node(self, file_node: str, log_info: Any):
        """
        Safely adds a log statement node to the graph.
        
        Defensive upgrades:
        - Coerces input safely.
        - Ensures ID is hashable.
        - Logs malformed entries.
        """
        try:
            if isinstance(log_info, str):
                log_message = log_info
                log_level = "INFO"
            elif isinstance(log_info, dict):
                log_message = log_info.get('message', '')
                log_level = log_info.get('level', 'INFO')
            else:
                log_message = str(log_info)
                log_level = "INFO"

            try:
                log_hash = hash(log_message)
            except Exception:
                log_hash = hash("<bad message>")

            log_id = f"Log: {log_hash}"
            log_node = log_id

            if not self.graph.has_node(log_node):
                self.graph.add_node(
                    log_node,
                    type="log_statement",
                    level=log_level,
                    message=log_message,
                    id=log_node
                )
                if 'total_logging_statements' not in self.stats or not isinstance(self.stats['total_logging_statements'], int):
                    self.stats['total_logging_statements'] = 0
                self.stats['total_logging_statements'] += 1
                logging.debug(f"Log node added: {log_node}")

            self.graph.add_edge(file_node, log_node, relation="USES")
            logging.debug(f"Edge added: {file_node} -> {log_node} with relation USES")

        except Exception as e:
            logging.warning(f"Failed to add log statement node: {e}")

    def _add_integration_node(self, file_node: str, integration: Any):
        """
        Safely adds an integration node to the graph.
        
        Accepts both dicts and fallback strings. Adds defensive logging for malformed entries.
        """
        try:
            if isinstance(integration, dict):
                integration_name = integration.get('name', 'unnamed_integration')
                integration_url = integration.get('url', '')
            elif isinstance(integration, str):
                integration_name = integration
                integration_url = ''
            else:
                integration_name = str(integration)
                integration_url = ''

            integration_node = f"Integration: {integration_name}"

            if not self.graph.has_node(integration_node):
                self.graph.add_node(
                    integration_node,
                    type="api_integration",
                    name=integration_name,
                    url=integration_url,
                    id=integration_node
                )
                if 'total_integrations' not in self.stats or not isinstance(self.stats['total_integrations'], int):
                    self.stats['total_integrations'] = 0
                self.stats['total_integrations'] += 1
                logging.debug(f"Integration node added: {integration_node}")

            self.graph.add_edge(file_node, integration_node, relation="INTEGRATES_WITH")
            logging.debug(f"Edge added: {file_node} -> {integration_node} with relation INTEGRATES_WITH")

        except Exception as e:
            logging.warning(f"Failed to add integration node: {e}")

    def _add_version_info(self, file_node: str, version_info: Any):
        """
        Add version information nodes to the graph from various formats.
        Handles malformed or inconsistent data gracefully.
        """
        try:
            if not isinstance(version_info, dict):
                logging.warning(f"Version info for {file_node} is not a dict: {version_info}")
                return

            for version_type, version_data in version_info.items():
                version_node = f"Version: {version_type}"

                # Defensive default if version_data isn't a dict
                constraints = ""
                if isinstance(version_data, dict):
                    constraints = version_data.get('constraints', '')
                elif isinstance(version_data, str):
                    constraints = version_data
                elif version_data is not None:
                    constraints = str(version_data)

                if not self.graph.has_node(version_node):
                    self.graph.add_node(
                        version_node,
                        type="version",
                        version_type=version_type,
                        constraints=constraints,
                        id=version_node
                    )
                    if 'total_version_constraints' not in self.stats or not isinstance(self.stats['total_version_constraints'], int):
                        self.stats['total_version_constraints'] = 0
                    self.stats['total_version_constraints'] += 1
                    logging.debug(f"Version node added: {version_node}")

                self.graph.add_edge(file_node, version_node, relation="HAS_VERSION")
                logging.debug(f"Edge added: {file_node} -> {version_node} with relation HAS_VERSION")

        except Exception as e:
            logging.warning(f"Failed to add version info for {file_node}: {e}")

    def _add_localization_usage_node(self, file_node: str, localization: Dict[str, Any]):
        """Add a localization usage node to the graph."""
        localization_path = localization.get('path', 'unknown_path')
        locale = localization.get('locale', 'unknown_locale')
        localization_node = f"i18n: {os.path.basename(localization_path)}"
        if not self.graph.has_node(localization_node):
            self.graph.add_node(
                localization_node,
                type="localization",
                path=localization_path,
                locale=locale,
                id=localization_node
            )
            self.stats['total_localizations'] += 1
        self.graph.add_edge(file_node, localization_node, relation="USES")

    def _process_build_file(self, file_path: str):
        """Process build configuration files."""
        try:
            build_type = None
            if file_path.endswith("setup.py") or file_path.endswith("setup.cfg"):
                build_type = "setuptools"
                dependencies = self.dependency_mapper.extract_setup_dependencies(file_path)
            elif file_path.endswith("requirements.txt"):
                build_type = "requirements"
                dependencies = self.dependency_mapper.extract_requirements(file_path)
            elif file_path.endswith("Pipfile"):
                build_type = "pipenv"
                dependencies = self.dependency_mapper.extract_pipfile_dependencies(file_path)
            elif file_path.endswith("pyproject.toml"):
                build_type = "poetry"
                dependencies = self.dependency_mapper.extract_pyproject_dependencies(file_path)
            else:
                dependencies = []

            # Add build script node
            build_node = f"Build: {os.path.relpath(file_path, self.directory)}"
            if not self.graph.has_node(build_node):
                self.graph.add_node(
                    build_node,
                    type="build_script",
                    path=os.path.relpath(file_path, self.directory),
                    build_tool=build_type,
                    id=build_node
                )
                self.stats['total_build_scripts'] += 1

            for dep in dependencies:
                dep_info = {
                    'name': dep.name,
                    'version': dep.version
                }
                self._add_dependency_node(build_node, dep_info)

        except Exception as e:
            logging.error(f"Error processing build file {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def _process_config_file(self, file_path: str):
        """Process configuration files."""
        try:
            relative_path = os.path.relpath(file_path, self.directory)
            config_info = self.config_parser.parse_config_file(file_path)
            if config_info:
                config_node = f"Config: {relative_path}"
                if not self.graph.has_node(config_node):
                    self.graph.add_node(
                        config_node,
                        type="config",
                        path=relative_path,
                        config_type=config_info.config_type.value,
                        id=config_node
                    )
                    self.stats['total_configs'] += 1
                # Link config to file
                file_node = f"File: {relative_path}"
                self.graph.add_edge(file_node, config_node, relation="CONFIGURED_BY")
        except AttributeError as ae:
            logging.error(f"AttributeError processing config file {file_path}: {str(ae)}")
            self.stats['files_with_errors'] += 1
        except Exception as e:
            logging.error(f"Error processing config file {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def _process_localization_file(self, file_path: str):
        """Process localization files."""
        try:
            relative_path = os.path.relpath(file_path, self.directory)
            locale = self.localization_processor.extract_locale(relative_path)
            localization_node = f"i18n: {os.path.basename(relative_path)}"
            if not self.graph.has_node(localization_node):
                self.graph.add_node(
                    localization_node,
                    type="localization",
                    path=relative_path,
                    locale=locale,
                    id=localization_node
                )
                self.stats['total_localizations'] += 1
            # Link localization to file
            file_node = f"File: {relative_path}"
            self.graph.add_edge(file_node, localization_node, relation="CONTAINS")

        except Exception as e:
            logging.error(f"Error processing localization file {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def _process_documentation_file(self, file_path: str):
        """Process documentation files like README.md and API docs."""
        try:
            relative_path = os.path.relpath(file_path, self.directory)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            doc_info = self.doc_analyzer.analyze_documentation(file_path)
            if doc_info:
                doc_node = f"Documentation: {relative_path}"
                if not self.graph.has_node(doc_node):
                    self.graph.add_node(
                        doc_node,
                        type="documentation",
                        path=file_path,
                        sections=[section.title for section in doc_info.sections],
                        id=doc_node
                    )
                project_node = "Project: Main"
                if not self.graph.has_node(project_node):
                    self.graph.add_node(project_node, type="project", name="Main Project", id=project_node)
                self.graph.add_edge(project_node, doc_node, relation="HAS_DOCUMENTATION")

        except Exception as e:
            logging.error(f"Error processing documentation file {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def _process_generic_file(self, file_path: str):
        """Process generic files that don't fall into specific categories."""
        try:
            relative_path = os.path.relpath(file_path, self.directory)
            file_info = self.file_processor.process_file(file_path)
            if file_info:
                file_node = f"File: {relative_path}"
                if not self.graph.has_node(file_node):
                    self.graph.add_node(
                        file_node,
                        type=file_info.type.value,
                        encoding=file_info.encoding or 'UTF-8',
                        fileType=file_info.extension,
                        purpose=file_info.purpose,
                        id=file_node
                    )
        except AttributeError as ae:
            logging.error(f"AttributeError processing generic file {file_path}: {str(ae)}")
            self.stats['files_with_errors'] += 1
        except Exception as e:
            logging.error(f"Error processing generic file {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def save_graph(self, output_path: str):
        """Save the knowledge graph to a JSON file."""
        try:
            # Convert graph to JSON format with explicit edges keyword to suppress FutureWarning
            data = json_graph.node_link_data(self.graph, edges="links")

            # Prepare metadata
            metadata = {
                "stats": {
                    "total_files": self.total_files,
                    "files_processed": self.files_processed,
                    "files_with_errors": self.stats['files_with_errors'],
                    "total_classes": self.stats['total_classes'],
                    "total_functions": self.stats['total_functions'],
                    "total_variables": self.stats['total_variables'],
                    "total_modules": len(self.stats['total_modules']),
                    "total_imports": self.stats['total_imports'],
                    "total_dependencies": len(self.stats['total_dependencies']),
                    "total_annotations": len(self.stats['total_annotations']),
                    "total_logging_statements": self.stats['total_logging_statements'],
                    "total_comments": self.stats['total_comments'],
                    "total_configs": self.stats['total_configs'],
                    "total_integrations": self.stats['total_integrations'],
                    "total_localizations": self.stats['total_localizations'],
                    "total_build_scripts": self.stats['total_build_scripts'],
                    "total_version_constraints": self.stats['total_version_constraints']
                },
                "build_info": {
                    "python_version": self.version_analyzer.extract_python_version(),
                    "build_tool": self.build_extractor.get_build_tool(),
                    "main_module": self.code_extractor.get_main_module()
                },
                "documentation": {
                    "readme_path": "README.md",
                    "api_docs": "docs/api.md",
                    "coverage_threshold": self.doc_analyzer.get_coverage_threshold()
                },
                "analysis_timestamp": datetime.now().isoformat(),
                "analyzed_directory": self.directory,
                "modules": list(self.stats['total_modules']),
                "dependencies": list(self.stats['total_dependencies'])
            }

            # Combine data and metadata
            output_data = {
                "graph": {
                    "directed": data['directed'],
                    "multigraph": data['multigraph'],
                    "nodes": data['nodes'],
                    "links": data['links']
                },
                "metadata": metadata
            }

            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2)

            # Log statistics
            logging.info(f"\nAnalysis Statistics:")
            for key, value in metadata['stats'].items():
                logging.info(f"{key}: {value}")

            logging.info(f"\nKnowledge graph saved to {output_path}")

        except AttributeError as ae:
            logging.error(f"AttributeError saving graph: {str(ae)}")
        except Exception as e:
            logging.error(f"Error saving graph: {str(e)}")

    def generate_example_output_structure(self):
        """Generate an example structure for reference."""
        example_output = {
            "graph": {
                "directed": True,
                "multigraph": False,
                "nodes": [
                    # Nodes will be populated here
                ],
                "links": [
                    # Links will be populated here
                ]
            },
            "metadata": {
                "stats": {
                    "total_files": 0,
                    "files_processed": 0,
                    "files_with_errors": 0,
                    "total_classes": 0,
                    "total_functions": 0,
                    "total_variables": 0,
                    "total_modules": 0,
                    "total_imports": 0,
                    "total_dependencies": 0,
                    "total_annotations": 0,
                    "total_logging_statements": 0,
                    "total_comments": 0,
                    "total_configs": 0,
                    "total_integrations": 0,
                    "total_localizations": 0,
                    "total_build_scripts": 0,
                    "total_version_constraints": 0
                },
                "build_info": {
                    "python_version": "",
                    "build_tool": "",
                    "main_module": ""
                },
                "documentation": {
                    "readme_path": "",
                    "api_docs": "",
                    "coverage_threshold": 0
                },
                "analysis_timestamp": "",
                "analyzed_directory": "",
                "modules": [],
                "dependencies": []
            }
        }
        return example_output

    def visualize_graph(self):
        """Visualize the knowledge graph."""
        try:
            import matplotlib.pyplot as plt

            # Create color map for different node types
            color_map = {
                "file": "#ADD8E6",           # Light blue
                "module": "#90EE90",         # Light green
                "class": "#FFE5B4",          # Peach
                "function": "#FFD700",       # Gold
                "variable": "#FFB6C1",       # Light pink
                "method": "#E6E6FA",         # Lavender
                "import": "#DDA0DD",         # Plum
                "dependency": "#8A2BE2",     # Blue Violet
                "decorator": "#FFA07A",      # Light Salmon
                "comment": "#C0C0C0",        # Silver
                "log_statement": "#808080",  # Gray
                "api_integration": "#FFDAB9",# Peach Puff
                "version": "#00CED1",        # Dark Turquoise
                "localization": "#40E0D0",   # Turquoise
                "build_script": "#B0E0E6",   # Powder Blue
                "documentation": "#F5DEB3",  # Wheat
                "project": "#98FB98",        # Pale Green
                "config": "#FFE4B5",         # Moccasin
            }

            # Set node colors
            node_colors = [
                color_map.get(self.graph.nodes[node].get("type", "file"), "lightgray")
                for node in self.graph.nodes()
            ]

            # Create figure and axis explicitly
            fig, ax = plt.subplots(figsize=(20, 15))

            # Calculate layout
            pos = nx.spring_layout(self.graph, k=1.5, iterations=50)

            # Draw the graph
            nx.draw(
                self.graph,
                pos,
                ax=ax,
                with_labels=True,
                node_color=node_colors,
                node_size=2000,
                font_size=8,
                font_weight="bold",
                arrows=True,
                edge_color="gray",
                arrowsize=20,
            )

            # Add legend
            legend_elements = [
                plt.Line2D(
                    [0], [0],
                    marker='o',
                    color='w',
                    markerfacecolor=color,
                    label=node_type.capitalize(),
                    markersize=10
                )
                for node_type, color in color_map.items()
            ]

            # Place legend outside the plot
            ax.legend(
                handles=legend_elements,
                loc='center left',
                bbox_to_anchor=(1.05, 0.5),
                title="Node Types"
            )

            # Set title
            ax.set_title("Python Code Knowledge Graph Visualization", pad=20)

            # Adjust layout to accommodate legend
            plt.subplots_adjust(right=0.85)

            # Show plot
            plt.show()

        except ImportError:
            print("Matplotlib is required for visualization. Install it using 'pip install matplotlib'.")

if __name__ == "__main__":
    try:
        print("Python Code Knowledge Graph Generator")
        print("------------------------------------")

        codebase_dir = input("Enter the path to the codebase directory: ").strip()
        if not os.path.exists(codebase_dir):
            raise ValueError(f"Directory does not exist: {codebase_dir}")

        # Create compression directory if it doesn't exist
        compression_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compression")
        os.makedirs(compression_dir, exist_ok=True)
        
        # Construct the output path to include the compression directory
        output_file = os.path.join(compression_dir, "python_code_knowledge_graph.json")

        # Create and analyze the codebase
        graph_generator = PythonCodeKnowledgeGraph(directory=codebase_dir)
        graph_generator.analyze_codebase()

        graph_generator.save_graph(output_file)

        # Wait until the file is confirmed to exist
        import time
        for _ in range(10):  # Retry for up to 10 seconds
            if os.path.exists(output_file):
                break
            time.sleep(1)
        else:
            raise FileNotFoundError(f"{output_file} was not created in time.")

        # Ask user if they want to visualize the graph
        visualize = input("\nWould you like to visualize the knowledge graph? (y/n): ").strip().lower()
        if visualize == 'y':
            print("Generating visualization...")
            graph_generator.visualize_graph()

        # Call the compression script
        try:
            import subprocess

            compression_script = os.path.join(compression_dir, 'compression.py')  

            # Output file path is already absolute from earlier change
            output_file_path = output_file

            subprocess.run(['python', compression_script, output_file_path], check=True)
            print(f"Compression script executed successfully on {output_file_path}")
        except FileNotFoundError:
            print(f"Error: Compression script not found at {compression_script}")
        except subprocess.CalledProcessError as e:
            print(f"Error executing compression script: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        print("\nDone.")
