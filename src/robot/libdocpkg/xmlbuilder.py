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

import os.path

from robot.errors import DataError
from robot.running import ArgInfo, ArgumentSpec
from robot.utils import ET, ETSource

from .model import LibraryDoc, KeywordDoc
from .datatypes import CustomDoc, EnumDoc, EnumMember, TypedDictDoc, TypedDictItem


class XmlDocBuilder:

    def build(self, path):
        spec = self._parse_spec(path)
        libdoc = LibraryDoc(name=spec.get('name'),
                            type=spec.get('type').upper(),
                            version=spec.find('version').text or '',
                            doc=spec.find('doc').text or '',
                            scope=spec.get('scope'),
                            doc_format=spec.get('format') or 'ROBOT',
                            source=spec.get('source'),
                            lineno=int(spec.get('lineno')) or -1)
        libdoc.inits = self._create_keywords(spec, 'inits/init', libdoc.source)
        libdoc.keywords = self._create_keywords(spec, 'keywords/kw', libdoc.source)
        libdoc.data_types.types = set(self._create_data_types(spec))
        return libdoc

    def _parse_spec(self, path):
        if not os.path.isfile(path):
            raise DataError("Spec file '%s' does not exist." % path)
        with ETSource(path) as source:
            root = ET.parse(source).getroot()
        if root.tag != 'keywordspec':
            raise DataError("Invalid spec file '%s'." % path)
        version = root.get('specversion')
        if version not in ('3', '4'):
            raise DataError(f"Invalid spec file version '{version}'. "
                            f"Supported versions are 3 and 4.")
        return root

    def _create_keywords(self, spec, path, lib_source):
        return [self._create_keyword(elem, lib_source) for elem in spec.findall(path)]

    def _create_keyword(self, elem, lib_source):
        # "deprecated" attribute isn't read because it is read from the doc
        # automatically. That should probably be changed at some point.
        return KeywordDoc(name=elem.get('name', ''),
                          args=self._create_arguments(elem),
                          doc=elem.find('doc').text or '',
                          shortdoc=elem.find('shortdoc').text or '',
                          tags=[t.text for t in elem.findall('tags/tag')],
                          source=elem.get('source') or lib_source,
                          lineno=int(elem.get('lineno', -1)))

    def _create_arguments(self, elem):
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
        for arg in elem.findall('arguments/arg'):
            name_elem = arg.find('name')
            if name_elem is None:
                continue
            name = name_elem.text
            setters[arg.get('kind')](name)
            default_elem = arg.find('default')
            if default_elem is not None:
                spec.defaults[name] = default_elem.text or ''
            type_elems = arg.findall('type')
            if not spec.types:
                spec.types = {}
            spec.types[name] = tuple(t.text for t in type_elems)
        return spec

    def _create_data_types(self, spec):
        enums = [self._create_enum_doc(dt)
                 for dt in spec.findall('datatypes/enums/enum')]
        typed_dicts = [self._create_typed_dict_doc(dt)
                       for dt in spec.findall('datatypes/typeddicts/typeddict')]
        custom = [self._create_custom_doc(dt)
                  for dt in spec.findall('datatypes/customs/custom')]
        return enums + typed_dicts + custom

    def _create_enum_doc(self, elem):
        return EnumDoc(name=elem.get('name'),
                       doc=elem.find('doc').text or '',
                       members=[EnumMember(name=member.get('name'),
                                           value=member.get('value'))
                                for member in elem.findall('members/member')])

    def _create_typed_dict_doc(self, elem):
        items = []
        for item in elem.findall('items/item'):
            required = item.get('required', None)
            if required is not None:
                required = required == 'true'
            items.append(TypedDictItem(key=item.get('key'),
                                       type=item.get('type'),
                                       required=required))
        return TypedDictDoc(name=elem.get('name'),
                            doc=elem.find('doc').text or '',
                            items=items)

    def _create_custom_doc(self, elem):
        return CustomDoc(name=elem.get('name'),
                         doc=elem.find('doc').text or '')
