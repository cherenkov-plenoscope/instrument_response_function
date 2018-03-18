import paramiko
import os


def read_scoop_hosts(scoop_hosts_path):
    """
    Reads in the scoop hosts text file and returns a list of these hosts. The 
    additional maximal number of threads of each host is ignored.

    Parameters
    ----------
    scoop_hosts_path        Path of the scoop hosts file
    """
    with open(scoop_hosts_path, 'r') as f:
        hosts = f.read()
    hosts = hosts.splitlines()

    only_host_adresses = []
    for host in hosts:
        only_host_adresses.append(host.split(' ')[0])

    return only_host_adresses


def kill_all_processes_on_hosts(process_wild_card, scoop_hosts):
    """
    Kills all processes matching the process_wild_card.
    Calls: 'pkill -f <process_wild_card>' on each scoop_host.

    Parameters
    ----------
    process_wild_card   A process-name to be killed on the scoop-hosts.

    scoop_hosts         A list of host adresses.
    """
    for hostname in scoop_hosts:
        with ScoopHost(hostname) as sch:
            sch.execute('pkill -f '+process_wild_card)


def remove_file_on_hosts(file_wild_card, scoop_hosts):
    """
    Performs: 'rm -rf <file_wild_card>' on the scoop-hosts.

    Parameters
    ----------
    file_wild_card 	A path on to be removed on the scoop-hosts    

    scoop_hosts         A list of host adresses.
    """
    for hostname in scoop_hosts:
        with ScoopHost(hostname) as sch:
            sch.execute('rm -rf '+file_wild_card)


def reset(scoop_hosts):
    kill_all_processes_on_hosts('corsika', scoop_hosts)
    kill_all_processes_on_hosts('mctracer', scoop_hosts)
    kill_all_processes_on_hosts('scoop', scoop_hosts)
    remove_file_on_hosts('/tmp/acp*', scoop_hosts)
    remove_file_on_hosts('/tmp/corsika*', scoop_hosts)


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
