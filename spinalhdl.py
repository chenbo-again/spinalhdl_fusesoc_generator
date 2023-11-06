#!/usr/bin/env python3
from copy import deepcopy
from fusesoc.capi2.generator import Generator
import os
import shutil
import shlex
import subprocess
import tempfile
import json
from fusesoc import utils
import sys


class SpinalHDLGenerator(Generator):
    def run(self):
        env = self.config.get('env', None)
        cwd = self.files_root
        # buildtool = self.config.get('buildtool', "sbt")
        buildtool = "sbt"
        spinal_project_path = os.path.join(cwd, self.config.get('spinal_project_path', '.'))
        entry_function = self.config.get('entry_function')
        copy_core = self.config.get('copy_core', False)
        if copy_core:
            tmp_dir = os.path.join(tempfile.mkdtemp(), 'core')
            shutil.copytree(spinal_project_path, tmp_dir,
                            ignore=shutil.ignore_patterns('out', 'generated'))
        spd = tmp_dir if copy_core else spinal_project_path
        target_directory = os.path.join(spd, self.config.get('target_directory', "generated"))

        files = self.config['output'].get('files', [])
        parameters = self.config['output'].get('parameters', {})
        
        config_parameter = deepcopy(self.config)
        config_parameter['target_directory'] = target_directory
        config_tmp_path = tempfile.mktemp()
        utils.yaml_fwrite(config_tmp_path, config_parameter)

        # Find build tool, first in root dir, then ./scripts dir then in path
        buildcmd = []
        if shutil.which(buildtool) is not None:
            buildcmd.append(shutil.which(buildtool))
        else:
            print("Build tool " + buildtool + " not found")
            exit(1)
        print("Using build tool from: " + buildcmd[0])

        # Define command and arguments based on build tool
        if buildtool == "sbt":
            args = ['runMain', entry_function,
                    '--core_file_path', config_tmp_path]
        else:
            raise
        
        # Concatenate environment variables from system + user defined
        d = os.environ
        if env:
            d.update(env)

        # Call build tool
        cmd = buildcmd + ["\"" + " ".join(args) + "\""]
        if os.getenv('EDALIZE_LAUNCHER'):
            cmd = [os.getenv('EDALIZE_LAUNCHER')] + cmd
        
        cmd = " ".join(cmd)
        print("Working dir:", spd)
        print("Running:", cmd)
        rc = subprocess.call(cmd, env=d, cwd=spd, shell=True)
        if rc:
            exit(1)
        if spd:
            filenames = []
            for f in files:
                for k in f:
                    filenames.append(k)

            for f in filenames:
                d = os.path.dirname(f)
                if d and not os.path.exists(d):
                    os.makedirs(d)
                shutil.copy2(os.path.join(spd, target_directory, f), f)

        self.add_files(files)

        for k, v in parameters.items():
            self.add_parameter(k, v)

    def _is_exe(self, fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)


g = SpinalHDLGenerator()
g.run()
g.write()
