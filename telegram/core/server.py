import getpass
import glob
import netrc
import os
from platform import architecture
import shutil
import subprocess
from sys import platform
import tarfile
import time
import requests

user_name = getpass.getuser()

core_dir = os.path.join(
    os.path.split(os.path.dirname(os.path.abspath(__file__)))[0], 'core'
)
server_source_directory_name = 'server'
heroku_server_directory_name = 'heroku-server'
local_server_directory_name = 'local-server'
task_directory_name = 'task'

server_process = None

heroku_url = 'https://cli-assets.heroku.com/heroku'


def setup_heroku_server(task_name):
    print("Heroku: Collecting files...")

    # Install Heroku CLI
    os_name = platform

    bit_architecture = 'x64' if architecture()[0] == '64bit' else 'x86'

    if os_name == 'win32':
        print('Windows not supported yet')
        return

    existing_heroku_directory_names = glob.glob(os.path.join(core_dir, 'heroku'))
    if len(existing_heroku_directory_names) == 0:
        if os.path.exists(os.path.join(core_dir, 'heroku.tar.gz')):
            os.remove(os.path.join(core_dir, 'heroku.tar.gz'))

        # Get the heroku client and unzip
        os.chdir(core_dir)

        r = requests.get(url=f'{heroku_url}-{os_name}-{bit_architecture}.tar.gz', allow_redirects=True)
        with open("heroku.tar.gz", "wb") as file:
            file.write(r.content)
        del r

        tar = tarfile.open("heroku.tar.gz", mode='r:gz')
        tar.extractall()
        tar.close()
        del tar

    heroku_directory_name = glob.glob(os.path.join(core_dir, 'heroku'))[0]
    heroku_directory_path = os.path.join(core_dir, heroku_directory_name)
    heroku_executable_path = os.path.join(heroku_directory_path, 'bin', 'heroku')

    server_source_directory_path = os.path.join(core_dir, server_source_directory_name)
    heroku_server_directory_path = os.path.join(core_dir, f'{heroku_server_directory_name}_{task_name}')

    # Delete old server files
    shutil.rmtree(heroku_server_directory_path, True)

    # Copy over a clean copy into the server directory
    shutil.copytree(server_source_directory_path, heroku_server_directory_path)

    print("Heroku: Starting server...")

    os.chdir(heroku_server_directory_path)
    os.system("git init")

    # get heroku credentials
    heroku_user_identifier = None
    while not heroku_user_identifier:
        try:
            subprocess.check_output([heroku_executable_path, 'auth:token'])
            heroku_user_identifier = netrc.netrc(
                os.path.join(os.path.expanduser("~"), '.netrc')
            ).hosts['api.heroku.com'][0]
        except subprocess.CalledProcessError:
            raise SystemExit(
                'A free Heroku account is required for launching MTurk tasks. '
                'Please register at https://signup.heroku.com/ and run `{} '
                'login` at the terminal to login to Heroku, and then run this '
                'program again.'.format(heroku_executable_path)
            )

    heroku_app_name = task_name[:30]

    while heroku_app_name[-1] == '-':
        heroku_app_name = heroku_app_name[:-1]

    # Create or attach to the server
    try:
        subprocess.check_output(
            [heroku_executable_path, 'create', heroku_app_name],
            stderr=subprocess.STDOUT,
            text=True
        )
    except subprocess.CalledProcessError as e:
        if 'is already taken' in e.output:
            print(e.output)
            do_continue = input(
                'An app is already running with that name, do you want to '
                'restart a new run with it (y/N): '
            )
            if do_continue != 'y':
                raise SystemExit('User chose not to re-run the app.')
            else:
                delete_heroku_server(task_name)
                try:
                    subprocess.check_output(
                        [heroku_executable_path, 'create', heroku_app_name],
                        stderr=subprocess.STDOUT,
                        text=True
                    )
                except subprocess.CalledProcessError as e:
                    shutil.rmtree(heroku_server_directory_path, True)
                    print(e.output)
                    raise SystemExit(
                        'Something unexpected happened trying to set up the '
                        'heroku server - please use the above printed error '
                        'to debug the issue however necessary.'
                    )
        else:
            shutil.rmtree(heroku_server_directory_path, True)
            print(e.output)
            raise SystemExit(
                'Something unexpected happened trying to set up the '
                'heroku server - please use the above printed error '
                'to debug the issue however necessary.'
            )
        # Enable WebSockets
    try:
        subprocess.check_output(
            [heroku_executable_path, 'features:enable', 'http-session-affinity']
        )
    except subprocess.CalledProcessError:  # Already enabled WebSockets
        pass

    # commit and push to the heroku server
    os.chdir(heroku_server_directory_path)
    os.system('git add -A')
    os.system('git commit -m "app"')
    os.system('git push -f heroku master')
    subprocess.check_output(
        [heroku_executable_path, 'ps:scale', 'web=1']
    )
    os.chdir(core_dir)

    # Clean up heroku files
    if os.path.exists(os.path.join(core_dir, 'heroku.tar.gz')):
        os.remove(os.path.join(core_dir, 'heroku.tar.gz'))

    shutil.rmtree(heroku_server_directory_path, True)

    return f'https://{heroku_app_name}.herokuapp.com'


def delete_heroku_server(task_name):
    heroku_directory_name = glob.glob(os.path.join(core_dir, 'heroku'))[0]
    heroku_directory_path = os.path.join(core_dir, heroku_directory_name)
    heroku_executable_path = os.path.join(heroku_directory_path, 'bin', 'heroku')

    heroku_app_name = task_name[:30]
    print(f"Heroku: Deleting server: {heroku_app_name}")
    subprocess.check_output([
        heroku_executable_path, 'destroy', heroku_app_name, '--confirm', heroku_app_name
    ])


def setup_local_server(task_name):
    global server_process
    print("Local Server: Collecting files...")

    server_source_directory_path = os.path.join(core_dir, server_source_directory_name)
    local_server_directory_path = os.path.join(
        core_dir, '{}_{}'.format(local_server_directory_name, task_name)
    )

    # Delete old server files
    shutil.rmtree(local_server_directory_path, True)

    # Copy over a clean copy into the server directory
    shutil.copytree(server_source_directory_path, local_server_directory_path)

    print("Local: Starting server...")

    os.chdir(local_server_directory_path)

    packages_installed = subprocess.call(['npm', 'install'])
    if packages_installed != 0:
        raise Exception(
            'please make sure npm is installed, otherwise view '
            'the above error for more info.'
        )

    server_process = subprocess.Popen(['node', 'server.js'])

    time.sleep(1)
    print(f'Server running locally with pid {server_process.pid}.')
    host = input('Please enter the public server address, like https://hostname.com: ')
    port = input('Please enter the port given above, likely 3000: ')
    return f'{host}:{port}'


def delete_local_server(task_name):
    global server_process
    print('Terminating server')
    server_process.terminate()
    server_process.wait()
    print('Cleaning temp directory')
    local_server_directory_path = os.path.join(core_dir, f'{local_server_directory_name}_{task_name}')
    shutil.rmtree(local_server_directory_path, True)


def setup_server(task_name, local=False):
    if local:
        return setup_local_server(task_name)
    else:
        return setup_heroku_server(task_name)


def delete_server(task_name, local=False):
    if local:
        delete_local_server(task_name)
    else:
        delete_heroku_server(task_name)
