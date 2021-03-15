#!/usr/bin/env python3

# Copyright (c) Facebook, Inc. and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""
Unit tests for exporting models via TorchScript (i.e. JIT compilation).
"""

import os
import regex
import unittest

import parlai.utils.testing as testing_utils
from parlai.agents.repeat_label.repeat_label import RepeatLabelAgent
from parlai.core.agents import create_agent
from parlai.core.params import ParlaiParser
from parlai.core.worlds import create_task
from parlai.utils.bpe import Gpt2BpeHelper


@testing_utils.skipUnlessGPU
@testing_utils.skipUnlessTorch17
class TestJit(unittest.TestCase):

    from parlai.scripts.jit_export import JitExport, ScriptableGpt2BpeHelper

    def test_token_splitter(self):
        """
        Test TorchScriptable code for splitting tokens against reference GPT-2 version.
        """

        # Params
        tasks = ['taskmaster2', 'convai2']
        compiled_pattern = regex.compile(Gpt2BpeHelper.PATTERN)

        with testing_utils.tempdir() as tmpdir:
            datapath = tmpdir

            for task in tasks:
                opt = JitExport.setup_args().parse_kwargs(
                    task=task, datatype='train:ordered', datapath=datapath
                )
                agent = RepeatLabelAgent(opt)
                teacher = create_task(opt, agent).get_task_agent()
                num_examples = teacher.num_examples()

                print(
                    f'\nStarting to test {num_examples:d} examples for the '
                    f'{task} task.'
                )
                for idx, message in enumerate(teacher):
                    if idx % 10000 == 0:
                        print(f'Testing example #{idx:d}.')
                    text = message['text']
                    canonical_tokens = regex.findall(compiled_pattern, text)
                    scriptable_tokens = ScriptableGpt2BpeHelper.findall(text)
                    self.assertEqual(canonical_tokens, scriptable_tokens)
                    if idx + 1 == num_examples:
                        break

    def test_jit_agent(self):
        """
        Test exporting a model to TorchScript and then testing it on sample data.
    
        """

        test_phrase = "Don't have a cow, man!"  # From test_bart.py

        with testing_utils.tempdir() as tmpdir:

            scripted_model_file = os.path.join(tmpdir, 'scripted_model.pt')

            # Export the BART model
            export_opt = JitExport.setup_args().parse_kwargs(
                model='bart', scripted_model_file=scripted_model_file
            )
            JitExport(export_opt).run()

            # Test the scripted BART model
            scripted_opt = ParlaiParser(True, True).parse_kwargs(
                model='jit', model_file=scripted_model_file
            )
            bart = create_agent(scripted_opt)
            bart.observe({'text': test_phrase, 'episode_done': True})
            act = bart.act()
            self.assertEqual(act['text'], test_phrase)


if __name__ == '__main__':
    unittest.main()
