import os,getpass,time
from .batch import Batch
from .job_status import JobStatus

def _default_item(resources, key, value) :
    if key not in resources :
        resources[key] = value


class Shell(Batch) :

    def check_status(self) :
        if self.check_finish_tag():
            return JobStatus.finished
        elif self.check_running():
            return JobStatus.running
        else:
            return JobStatus.terminated
        ## warn: cannont distinguish terminated from unsubmitted.

    def check_running(self):
        uuid_names = self.context.job_uuid
        ## Check if the uuid.sub is running on remote machine
        cnt = 0
        ret, stdin, stdout, stderr = self.context.block_call("ps aux | grep %s"%uuid_names)
        response_list = stdout.read().decode('utf-8').split("\n")
        for response in response_list:
            if  uuid_names + ".sub" in response:
                return True
        return False
    
    def exec_sub_script(self, script_str):
        self.context.write_file(self.sub_script_name, script_str)
        self.proc = self.context.call('cd %s && exec bash %s' % (self.context.remote_root, self.sub_script_name))

    def default_resources(self, res_) :
        if res_ is None :
            res = {}
        else:
            res = res_
        _default_item(res, 'task_per_node', 1)
        _default_item(res, 'module_list', [])
        _default_item(res, 'module_unload_list', [])
        _default_item(res, 'source_list', [])
        _default_item(res, 'envs', {})
        _default_item(res, 'with_mpi', False)
        _default_item(res, 'cuda_multi_tasks', False)
        _default_item(res, 'allow_failure', False)
        return res

    def sub_script_head(self, resources) :
        envs = resources['envs']
        module_list = resources['module_list']
        module_unload_list = resources['module_unload_list']
        task_per_node = resources['task_per_node']
        source_list = resources['source_list']
        
        ret = ''
        ret += ('#!/bin/bash\n\n')
        # fp.write('set -euo pipefail\n')
        for key in envs.keys() :
            ret += ('export %s=%s\n' % (key, envs[key]))
        ret += ('\n')
        for ii in module_unload_list :
            ret += ('module unload %s\n' % ii)
        ret += ('\n')
        for ii in module_list :
            ret += ('module load %s\n' % ii)
        ret += ('\n')
        for ii in source_list :
            ret += ('source %s\n' % ii)
        ret += ('\n')
        return ret

    def sub_script_cmd(self,
                       cmd,
                       arg,
                       res) :
        _cmd = cmd.split('1>')[0].strip()
        if res['with_mpi']:
            _cmd = 'mpirun -n %d %s %s' % (res['task_per_node'],  _cmd, arg)
        else :
            _cmd = '%s %s' % (_cmd, arg)
        return _cmd
        
    def make_non_blocking(self, inner_script, step_res=None):
        return f"({inner_script})&\n"