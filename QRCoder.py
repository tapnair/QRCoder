import adsk.core
import traceback

from . import config
from .utils import check_apper
check_apper()

try:
    from .apper import apper
    from .commands.QRCodeMaker import QRCodeMaker

    my_addin = apper.FusionApp(config.app_name, config.company_name, False)
    my_addin.root_path = config.app_path

    # General command showing inputs and user interaction
    my_addin.add_command(
        'Create QR Code',
        QRCodeMaker,
        {
            'cmd_description': 'Generate QR Code geometry by encoding a message with various options.',
            'cmd_id': 'make_qr',
            'workspace': 'FusionSolidEnvironment',
            'toolbar_panel_id': 'Commands',
            'cmd_resources': 'make_qr_icons',
            'command_visible': True,
            'command_promoted': True,
            'is_make_qr': True
        }
    )

    my_addin.add_command(
        'Import QR Code',
        QRCodeMaker,
        {
            'cmd_description': 'Generate QR Code geometry by importing definition from a csv file.',
            'cmd_id': 'import_qr',
            'workspace': 'FusionSolidEnvironment',
            'toolbar_panel_id': 'Commands',
            'cmd_resources': 'csv_qr_icons',
            'command_visible': True,
            'command_promoted': True,
            'is_make_qr': False
        }
    )

except:
    app = adsk.core.Application.get()
    ui = app.userInterface
    if ui:
        ui.messageBox('Initialization Failed: {}'.format(traceback.format_exc()))

# Set to True to display various useful messages when debugging your app
debug = False


def run(context):
    my_addin.run_app()


def stop(context):
    my_addin.stop_app()

