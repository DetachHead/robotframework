#  Copyright 2008-2015 Nokia Networks
#  Copyright 2016-     Robot Framework Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import json
import os.path

from robot.running import ArgInfo, ArgumentSpec
from robot.errors import DataError

from .datatypes import CustomDoc, EnumDoc, EnumMember, TypedDictDoc, TypedDictItem
from .model import LibraryDoc, KeywordDoc


class JsonDocBuilder:

    def build(self, path):
        spec = self._parse_spec_json(path)
        return self.build_from_dict(spec)

    def build_from_dict(self, spec):
        libdoc = LibraryDoc(name=spec['name'],
                            doc=spec['doc'],
                            version=spec['version'],
                            type=spec['type'],
                            scope=spec['scope'],
                            doc_format=spec['docFormat'],
                            source=spec['source'],
                            lineno=int(spec.get('lineno', -1)))
        libdoc.inits = [self._create_keyword(kw) for kw in spec['inits']]
        libdoc.keywords = [self._create_keyword(kw) for kw in spec['keywords']]
        libdoc.data_types.types = set(self._create_data_types(spec['dataTypes']))
        return libdoc

    def _parse_spec_json(self, path):
        if not os.path.isfile(path):
            raise DataError("Spec file '%s' does not exist." % path)
        with open(path) as json_source:
            libdoc_dict = json.load(json_source)
        return libdoc_dict

    def _create_keyword(self, kw):
        return KeywordDoc(name=kw.get('name'),
                          args=self._create_arguments(kw['args']),
                          doc=kw['doc'],
                          shortdoc=kw['shortdoc'],
                          tags=kw['tags'],
                          source=kw['source'],
                          lineno=int(kw.get('lineno', -1)))

    def _create_arguments(self, arguments):
        spec = ArgumentSpec()
        setters = {
            ArgInfo.POSITIONAL_ONLY: spec.positional_only.append,
            ArgInfo.POSITIONAL_ONLY_MARKER: lambda value: None,
            ArgInfo.POSITIONAL_OR_NAMED: spec.positional_or_named.append,
            ArgInfo.VAR_POSITIONAL: lambda value: setattr(spec, 'var_positional', value),
            ArgInfo.NAMED_ONLY_MARKER: lambda value: None,
            ArgInfo.NAMED_ONLY: spec.named_only.append,
            ArgInfo.VAR_NAMED: lambda value: setattr(spec, 'var_named', value),
        }
        for arg in arguments:
            name = arg['name']
            setters[arg['kind']](name)
            default = arg.get('defaultValue')
            if default is not None:
                spec.defaults[name] = default
            arg_types = arg['types']
            if not spec.types:
                spec.types = {}
            spec.types[name] = tuple(arg_types)
        return spec

    def _create_data_types(self, data_types):
        enums = [self._create_enum_doc(dt)
                 for dt in data_types.get('enums', [])]
        typed_dicts = [self._create_typed_dict_doc(dt)
                       for dt in data_types.get('typedDicts', [])]
        customs = [self._create_custom_doc(dt)
                   for dt in data_types.get('customs', [])]
        return enums + typed_dicts + customs

    def _create_enum_doc(self, data):
        return EnumDoc(name=data['name'],
                       doc=data['doc'],
                       members=[EnumMember(member['name'], member['value'])
                                for member in data['members']])

    def _create_typed_dict_doc(self, data):
        return TypedDictDoc(name=data['name'],
                            doc=data['doc'],
                            items=[TypedDictItem(item['key'], item['type'],
                                                 item.get('required'))
                                   for item in data['items']])

    def _create_custom_doc(self, data):
        return CustomDoc(name=data['name'], doc=data['doc'])
