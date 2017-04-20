import paramiko
import os


def read_scoop_hosts(scoop_hosts_path):
    with open(scoop_hosts_path, 'r') as f:
        hosts = f.read()
    hosts = hosts.splitlines()

    only_host_adresses = []
    for host in hosts:
        only_host_adresses.append(host.split(' ')[0])

    return only_host_adresses


def kill_scoop_on_hosts(scoop_hosts):
    for hostname in scoop_hosts:
        with ScoopHost(hostname) as sch:
            sch.execute('pkill -f scoop')


def remove_temporary_simulation_files_on_hosts(scoop_hosts):
    for hostname in scoop_hosts:
        with ScoopHost(hostname) as sch:
            sch.execute('rm -rf /tmp/acp_effective_area_*')
            sch.execute('rm -rf /tmp/corsika_*') 


class ScoopHost(object):
    def __init__(self, hostname):
        self._hostname = hostname
        self._ssh = self._make_ssh_client()

    def _make_ssh_client(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=self._hostname)
        return ssh

    def execute(self, command, out_path=None):
        """
        Executes the command on the remote host and returns the exit status
        of the command when the process on the remote host is done (blocking).

        Parameters
        ----------
        command         The command string to be executed on the remote host

        [out_path]      A path to store the stdout and stderr streams of the
                        command. Two text files will be created:
                        'out_path.stdout' and 'out_path.stderr'
                        The suffix 'stdout' and 'stderr' is appended to the
                        out_path.
        """
        transport = self._ssh.get_transport()
        channel = transport.open_session()
        channel.exec_command(command)
        if out_path is not None:
            stdout = channel.makefile('r')
            stderr = channel.makefile_stderr('r')
        exit_status = channel.recv_exit_status()
        if out_path is not None:
            self._write_out_stream_to_file(stdout, out_path+'.stdout')
            self._write_out_stream_to_file(stderr, out_path+'.stderr')
        return exit_status

    def _write_out_stream_to_file(self, stream, path):
        f = open(path, 'w')
        for line in stream.readlines():
            f.write(line)
        f.close()

    def __repr__(self):
        out = 'ScoopHost('
        out+= self._hostname
        out+= ')'
        return out

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ssh.close()
