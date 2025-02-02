# This file is part of CycloneDX Python Lib
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) OWASP Foundation. All Rights Reserved.


import random
from contextlib import redirect_stderr, redirect_stdout
from glob import glob
from io import StringIO
from os.path import basename, dirname, join
from typing import Any, Generator
from unittest import TestCase

from cyclonedx.schema import OutputFormat, SchemaVersion
from ddt import ddt, named_data

from cyclonedx_py._internal.cli import run as run_cli
from tests import INFILES_DIRECTORY, SUPPORTED_OF_SV, SnapshotMixin, make_comparable

lockfiles = glob(join(INFILES_DIRECTORY, 'poetry', '*', '*', 'poetry.lock'))
projectdirs = list(dirname(lockfile) for lockfile in lockfiles)

test_data = tuple(
    (f'{basename(dirname(projectdir))}-{basename(projectdir)}-{sv.name}-{of.name}', projectdir, sv, of)
    for projectdir in projectdirs
    for of, sv in SUPPORTED_OF_SV
)


def test_data_file_filter(s: str) -> Generator[Any, None, None]:
    return ((n, d, sv, of) for n, d, sv, of in test_data if s in n)


@ddt
class TestCliPoetry(TestCase, SnapshotMixin):

    def test_fails_with_dir_not_found(self) -> None:
        _, projectdir, sv, of = random.choice(test_data)  # nosec B311
        with StringIO() as err, StringIO() as out:
            err.name = '<fakeerr>'
            out.name = '<fakeout>'
            with redirect_stderr(err), redirect_stdout(out):
                res = run_cli(argv=[
                    'poetry',
                    '-vvv',
                    '--sv', sv.to_version(),
                    '--of', of.name,
                    '--outfile=-',
                    'something-that-must-not-exist.testing'])
            err = err.getvalue()
            out = out.getvalue()
        self.assertNotEqual(0, res, err)
        self.assertIn('Could not open pyproject file: something-that-must-not-exist.testing', err)

    def test_fails_with_groups_not_found(self) -> None:
        projectdir = random.choice(projectdirs)  # nosec B311
        with StringIO() as err, StringIO() as out:
            err.name = '<fakeerr>'
            out.name = '<fakeout>'
            with redirect_stderr(err), redirect_stdout(out):
                res = run_cli(argv=[
                    'poetry',
                    '-vvv',
                    '--with', 'MNE-with-A',
                    '--with', 'MNE-with-B,MNE-with-C',
                    '--without', 'MNE-without-A',
                    '--without', 'MNE-without-B,MNE-without-C',
                    '--only', 'MNE-only-A',
                    '--only', 'MNE-only-B,MNE-only-C',
                    projectdir])
            err = err.getvalue()
            out = out.getvalue()
        self.assertNotEqual(0, res, err)
        self.assertIn('Group(s) not found:'
                      " 'MNE-only-A' (via only),"
                      " 'MNE-only-B' (via only),"
                      " 'MNE-only-C' (via only),"
                      " 'MNE-with-A' (via with),"
                      " 'MNE-with-B' (via with),"
                      " 'MNE-with-C' (via with),"
                      " 'MNE-without-A' (via without),"
                      " 'MNE-without-B' (via without),"
                      " 'MNE-without-C' (via without)", err)

    def test_fails_with_extras_not_found(self) -> None:
        projectdir = random.choice(projectdirs)  # nosec B311
        with StringIO() as err, StringIO() as out:
            err.name = '<fakeerr>'
            out.name = '<fakeout>'
            with redirect_stderr(err), redirect_stdout(out):
                res = run_cli(argv=[
                    'poetry',
                    '-vvv',
                    '-E', 'MNE-extra-C,MNE-extra-B',
                    '--extras', 'MNE-extra-A',
                    projectdir])
            err = err.getvalue()
            out = out.getvalue()
        self.assertNotEqual(0, res, err)
        self.assertIn('Extra(s) ['
                      'MNE-extra-A,'
                      'MNE-extra-B,'
                      'MNE-extra-C'
                      '] not specified', err)

    @named_data(*test_data)
    def test_plain_as_expected(self, projectdir: str, sv: SchemaVersion, of: OutputFormat) -> None:
        with StringIO() as err, StringIO() as out:
            err.name = '<fakeerr>'
            out.name = '<fakeout>'
            with redirect_stderr(err), redirect_stdout(out):
                res = run_cli(argv=[
                    'poetry',
                    '-vvv',
                    '--sv', sv.to_version(),
                    '--of', of.name,
                    '--output-reproducible',
                    '--outfile=-',
                    projectdir])
            err = err.getvalue()
            out = out.getvalue()
        self.assertEqual(0, res, err)
        self.assertEqualSnapshot(out, 'plain', projectdir, sv, of)

    @named_data(*test_data_file_filter('group-deps'))
    def test_with_groups_as_expected(self, projectdir: str, sv: SchemaVersion, of: OutputFormat) -> None:
        with StringIO() as err, StringIO() as out:
            err.name = '<fakeerr>'
            out.name = '<fakeout>'
            with redirect_stderr(err), redirect_stdout(out):
                res = run_cli(argv=[
                    'poetry',
                    '-vvv',
                    '--with', 'groupA',
                    '--without', 'groupB,dev',
                    '--sv', sv.to_version(),
                    '--of', of.name,
                    '--output-reproducible',
                    '--outfile=-',
                    projectdir])
            err = err.getvalue()
            out = out.getvalue()
        self.assertEqual(0, res, err)
        self.assertEqualSnapshot(out, 'some-groups', projectdir, sv, of)

    @named_data(*test_data_file_filter('group-deps'))
    def test_only_groups_as_expected(self, projectdir: str, sv: SchemaVersion, of: OutputFormat) -> None:
        with StringIO() as err, StringIO() as out:
            err.name = '<fakeerr>'
            out.name = '<fakeout>'
            with redirect_stderr(err), redirect_stdout(out):
                res = run_cli(argv=[
                    'poetry',
                    '-vvv',
                    '--only', 'groupB',
                    '--sv', sv.to_version(),
                    '--of', of.name,
                    '--output-reproducible',
                    '--outfile=-',
                    projectdir])
            err = err.getvalue()
            out = out.getvalue()
        self.assertEqual(0, res, err)
        self.assertEqualSnapshot(out, 'only-groups', projectdir, sv, of)

    @named_data(*test_data_file_filter('group-deps'),
                *test_data_file_filter('main-and-dev'))
    def test_nodev_as_expected(self, projectdir: str, sv: SchemaVersion, of: OutputFormat) -> None:
        with StringIO() as err, StringIO() as out:
            err.name = '<fakeerr>'
            out.name = '<fakeout>'
            with redirect_stderr(err), redirect_stdout(out):
                res = run_cli(argv=[
                    'poetry',
                    '-vvv',
                    '--no-dev',
                    '--sv', sv.to_version(),
                    '--of', of.name,
                    '--output-reproducible',
                    '--outfile=-',
                    projectdir])
            err = err.getvalue()
            out = out.getvalue()
        self.assertEqual(0, res, err)
        self.assertEqualSnapshot(out, 'no-dev', projectdir, sv, of)

    @named_data(*test_data_file_filter('with-extras'))
    def test_with_extras_as_expected(self, projectdir: str, sv: SchemaVersion, of: OutputFormat) -> None:
        with StringIO() as err, StringIO() as out:
            err.name = '<fakeerr>'
            out.name = '<fakeout>'
            with redirect_stderr(err), redirect_stdout(out):
                res = run_cli(argv=[
                    'poetry',
                    '-vvv',
                    '-E', 'my-extra',
                    '--sv', sv.to_version(),
                    '--of', of.name,
                    '--output-reproducible',
                    '--outfile=-',
                    projectdir])
            err = err.getvalue()
            out = out.getvalue()
        self.assertEqual(0, res, err)
        self.assertEqualSnapshot(out, 'some-extras', projectdir, sv, of)

    def assertEqualSnapshot(self, actual: str,  # noqa:N802
                            purpose: str,
                            projectdir: str,
                            sv: SchemaVersion,
                            of: OutputFormat
                            ) -> None:  # noqa:N802
        super().assertEqualSnapshot(
            make_comparable(actual, of),
            join(
                'poetry',
                f'{purpose}_{basename(dirname(projectdir))}_{basename(projectdir)}_{sv.to_version()}.{of.name.lower()}'
            )
        )
