import os
import urllib.request
import zipfile

import adsk.core

REPO = 'apper'
REPO_URL = 'https://github.com/tapnair/apper/archive/master.zip'

from . import config


def _get_apper(base_dir: str) -> bool:
    zip_name = os.path.join(base_dir, f'{REPO}.zip')
    p_bar = ProgressBar()

    # Download Apper
    try:
        p_bar.start()
        urllib.request.urlretrieve(REPO_URL, zip_name)
    except Exception as e:
        _install_error(
            f'Failed to connect to download site.  Try manually downloading from:\n'
            f'<a href={REPO_URL}>{REPO_URL}</a>'
        )
        raise e

    # Unzip and rename
    try:
        p_bar.update_progress(f'Extracting Zip: {zip_name}')
        with zipfile.ZipFile(zip_name, 'r') as zip_ref:
            zip_ref.extractall(base_dir)
        os.rename(os.path.join(base_dir, f'{REPO}-master', ''), os.path.join(base_dir, f'{REPO}', ''))
        os.remove(zip_name)

    except Exception as e:
        _install_error(
            f'Failed to unzip or rename downloaded file.  Try manually unzipping from:\n {zip_name}\n'
               f'Make sure the directory is renamed from "apper-master" to "apper"'
        )
        raise e

    return True


def _install_error(message):
    app = adsk.core.Application.get()
    app.userInterface.messageBox(f'Apper installation encountered a problem:\n{message}')


def _confirm_apper():
    app = adsk.core.Application.get()

    res = app.userInterface.messageBox(
        '<html>'
        f"You need to installer apper to run this addin: {config.app_name}.<br>"
        f"Learn more at:<br>"
        f" <a href=http://apper.readthedocs.io/en/latest/>http://apper.readthedocs.io/en/latest/</a><br>"
        f"Press <b>Yes</b> to confirm."
        '</html>',
        "Apper Installation",
        adsk.core.MessageBoxButtonTypes.YesNoButtonType,
        adsk.core.MessageBoxIconTypes.QuestionIconType,
    )

    if res != adsk.core.DialogResults.DialogYes:
        raise PermissionError("User refused to install apper dependency")
    else:
        return True


def check_apper():
    if os.path.exists(os.path.join(config.app_path, 'apper', 'apper')):
        return True
    else:
        _install_apper()


def _install_apper():
    result_confirm = _confirm_apper()

    if result_confirm:
        result_install = _get_apper(config.app_path)
        if result_install:
            return
        else:
            raise RuntimeError("Apper could not be installed")


class ProgressBar:
    def __init__(self):
        app = adsk.core.Application.get()
        self.progress_bar = app.userInterface.createProgressDialog()
        self.progress_bar.isCancelButtonShown = False

    def start(self):
        self.progress_bar.reset()
        self.progress_bar.show("Installing Apper", f"Downloading File", 0, 3, 0)
        adsk.doEvents()

    def update_progress(self, message):
        self.progress_bar.progressValue += 1
        self.progress_bar.message = message
        adsk.doEvents()

    def finish(self):
        self.progress_bar.hide()
