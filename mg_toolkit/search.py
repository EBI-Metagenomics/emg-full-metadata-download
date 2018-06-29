#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2018 EMBL - European Bioinformatics Institute
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import requests
import html
from jsonapi_client import Session
from jsonapi_client.exceptions import DocumentError
from pandas import DataFrame


from .utils import (
    API_BASE, SEQ_URL
)

logger = logging.getLogger(__name__)


def sequence_search(args):

    """
    Process given fasta file
    """
    for s in args.sequence:
        with open(s) as f:
            sequence = f.read()
            logger.debug("Sequence %s" % sequence)
            seq = SequenceSearch(sequence)
            seq.save_to_csv(seq.fetch_metadata())


class SequenceSearch(object):

    """
    Helper tool allowing to download original metadata for the given accession.
    """

    sequence = None

    def __init__(self, sequence, *args, **kwargs):
        self.sequence = sequence

    def analyse_sequence(self):
        data = {
            "seqdb": "full",
            "seq": self.sequence,
        }
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        return requests.post(SEQ_URL, data=data, headers=headers)

    def fetch_metadata(self):
        csv_rows = {}
        with Session(API_BASE) as s:
            for h in self.analyse_sequence().json()['results']['hits']:
                acc2 = h.get('acc2', None)
                if acc2 is not None:
                    for accession in acc2.split(","):
                        accession = accession.strip("...")
                        logger.debug("Accession %s" % accession)
                        uuid = "{n} {a}".format(
                            **{'n': h['name'], 'a': accession})
                        csv_rows[uuid] = dict()
                        csv_rows[uuid]['accessions'] = accession
                        csv_rows[uuid]['kg'] = h.get('kg', '')
                        csv_rows[uuid]['taxid'] = h.get('taxid', '')
                        csv_rows[uuid]['name'] = h.get('name', '')
                        csv_rows[uuid]['desc'] = h.get('desc', '')
                        csv_rows[uuid]['pvalue'] = h.get('pvalue', '')
                        csv_rows[uuid]['species'] = h.get('species', '')
                        csv_rows[uuid]['score'] = h.get('score', '')
                        csv_rows[uuid]['evalue'] = h.get('evalue', '')
                        csv_rows[uuid]['nreported'] = h.get('nreported', '')
                        csv_rows[uuid]['uniprot'] = ",".join(
                            [i[0] for i in h.get('uniprot_link', [])])

                        _meta = {}
                        sample = None
                        try:
                            sample = s.get('samples', accession).resource
                        except DocumentError:
                            try:
                                run = s.get('runs', accession).resource
                                sample = run.sample
                            except DocumentError:
                                pass

                        if sample is not None:
                            for m in sample.sample_metadata:
                                unit = html.unescape(m['unit']) if m['unit'] else ""  # noqa
                                _meta[m['key'].replace(" ", "_")] = "{value} {unit}".format(value=m['value'], unit=unit)  # noqa
                        csv_rows[uuid].update(_meta)
        return csv_rows

    def save_to_csv(self, csv_rows, filename=None):
        df = DataFrame(csv_rows).T
        df.index.name = 'name'
        if filename is None:
            filename = "{}.csv".format('search_metadata')
        df.to_csv(filename)