"""
QRCoder, a Fusion 360 add-in
================================
QRCoder is a Fusion 360 add-in for the creation of 3D QR Codes.

:copyright: (c) 2021 by Patrick Rainsberry.
:license: MIT, see LICENSE for more details.


THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


QRCoder leverages the pyqrcode library:

    https://github.com/mnooner256/pyqrcode
    Copyright (c) 2013, Michael Nooner
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:
        * Redistributions of source code must retain the above copyright
          notice, this list of conditions and the following disclaimer.
        * Redistributions in binary form must reproduce the above copyright
          notice, this list of conditions and the following disclaimer in the
          documentation and/or other materials provided with the distribution.
        * Neither the name of the copyright holder nor the names of its
          contributors may be used to endorse or promote products derived from
          this software without specific prior written permission

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
    AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
    IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
    ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
    DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
    ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import csv
import os.path

import adsk.core
import adsk.fusion
import adsk.cam

from ..apper import apper
from .. import config

# Defaults
BLOCK = '.5 in'
HEIGHT = '.25 in'
BASE = '.25 in'
MESSAGE = 'https://tapnair.github.io/QRCoder/'

# File assumed to be in script root directory
FILE_NAME = 'QR-17x.csv'


def get_target_body(sketch_point):
    ao = apper.AppObjects()
    target_collection = ao.root_comp.findBRepUsingPoint(
        sketch_point.worldGeometry, adsk.fusion.BRepEntityTypes.BRepBodyEntityType, -1.0, True
    )

    if target_collection.count > 0:
        return target_collection.item(0)
    else:
        return None


def make_real_geometry(target_body: adsk.fusion.BRepBody, temp_body: adsk.fusion.BRepBody):
    ao = apper.AppObjects()

    if target_body is None:
        component = ao.design.activeComponent
    else:
        component = target_body.parentComponent

    base_feature = component.features.baseFeatures.add()
    base_feature.startEdit()
    component.bRepBodies.add(temp_body, base_feature)
    base_feature.finishEdit()

    if target_body is not None:
        tools = adsk.core.ObjectCollection.create()
        tools.add(base_feature.bodies.item(0))
        combine_input = component.features.combineFeatures.createInput(component.bRepBodies.item(0), tools)
        component.features.combineFeatures.add(combine_input)


def clear_graphics(graphics_group: adsk.fusion.CustomGraphicsGroup):
    for entity in graphics_group:
        if entity.isValid:
            entity.deleteMe()


def make_graphics(t_body: adsk.fusion.BRepBody, graphics_group: adsk.fusion.CustomGraphicsGroup):
    clear_graphics(graphics_group)
    color = adsk.core.Color.create(250, 162, 27, 255)
    color_effect = adsk.fusion.CustomGraphicsSolidColorEffect.create(color)
    graphics_body = graphics_group.addBRepBody(t_body)
    graphics_body.color = color_effect


def get_qr_temp_geometry(qr_data, input_values):
    side: float = input_values['block_size']
    height: float = input_values['block_height']
    base: float = input_values['base_height']
    sketch_point: adsk.fusion.SketchPoint = input_values['sketch_point'][0]

    x_dir = sketch_point.parentSketch.xDirection
    x_dir.normalize()
    y_dir = sketch_point.parentSketch.yDirection
    y_dir.normalize()
    z_dir = x_dir.crossProduct(y_dir)
    z_dir.normalize()

    qr_size = len(qr_data)
    middle_point = sketch_point.worldGeometry
    start_point = middle_point.copy()

    x_start_move = x_dir.copy()
    x_start_move.scaleBy((.5 * side) * (1 - qr_size))
    start_point.translateBy(x_start_move)

    y_start_move = y_dir.copy()
    y_start_move.scaleBy((.5 * side) * (qr_size - 1))
    start_point.translateBy(y_start_move)

    z_start_move = z_dir.copy()
    z_start_move.scaleBy((.5 * height) + base)
    start_point.translateBy(z_start_move)

    base_point = middle_point.copy()
    z_base_move = z_dir.copy()
    z_base_move.scaleBy((.5 * base))
    base_point.translateBy(z_base_move)

    b_mgr = adsk.fusion.TemporaryBRepManager.get()

    has_base = True
    if base > 0:
        full_size = side * qr_size
        base_t_box = adsk.core.OrientedBoundingBox3D.create(base_point, x_dir, y_dir, full_size, full_size, base)
        base_t_body = b_mgr.createBox(base_t_box)
    else:
        has_base = False

    for i, row in enumerate(qr_data):
        for j, col in enumerate(row):
            if int(col) == 1:
                x_move = x_dir.copy()
                y_move = y_dir.copy()
                x_move.scaleBy(j * side)
                y_move.scaleBy(-1 * i * side)

                c_point = start_point.copy()
                c_point.translateBy(x_move)
                c_point.translateBy(y_move)

                b_box = adsk.core.OrientedBoundingBox3D.create(c_point, x_dir, y_dir, side, side, height + base)
                t_body = b_mgr.createBox(b_box)

                if not has_base:
                    base_t_body = t_body
                    has_base = True
                else:
                    b_mgr.booleanOperation(base_t_body, t_body, adsk.fusion.BooleanTypes.UnionBooleanType)

    return base_t_body


def import_qr_from_file(file_name):
    qr_data = []

    if os.path.exists(file_name):
        with open(file_name, newline='') as f:
            reader = csv.reader(f)
            qr_data = list(reader)

    return qr_data


@apper.lib_import(config.lib_path)
def build_qr_code(message, args):
    import pyqrcode
    try:
        qr = pyqrcode.create(message, **args)
        qr_text = qr.text(quiet_zone=0)
        qr_data = [[char for char in y] for y in (x.strip() for x in qr_text.splitlines()) if y]
        return qr_data

    except ValueError as e:
        ao = apper.AppObjects()
        ao.ui.messageBox(f'Problem with inputs: {e}')
        return []


def make_qr_from_message(input_values):
    message: str = input_values['message']
    use_user_size: bool = input_values['use_user_size']
    user_size: int = input_values['user_size']
    mode: str = input_values['mode']
    error_type: str = input_values['error_type']

    args = {}
    if use_user_size:
        args['version'] = user_size
    if mode != 'Automatic':
        args['mode'] = mode
    if error_type != 'Automatic':
        args['error'] = error_type

    success = apper.check_dependency('pyqrcode', config.lib_path)

    if success:
        qr_data = build_qr_code(message, args)
        return qr_data


def add_make_inputs(inputs: adsk.core.CommandInputs):
    drop_style = adsk.core.DropDownStyles.TextListDropDownStyle
    inputs.addStringValueInput('message', 'Value to encode', MESSAGE)

    inputs.addBoolValueInput('use_user_size', 'Specify size?', True, '', False)
    size_spinner = inputs.addIntegerSpinnerCommandInput('user_size', 'QR Code Size (Version)', 1, 40, 1, 5)
    size_spinner.isEnabled = False
    size_spinner.isVisible = False

    mode_drop_down = inputs.addDropDownCommandInput('mode', 'Encoding Mode', drop_style)
    mode_items = mode_drop_down.listItems
    mode_items.add('Automatic', True, '')
    mode_items.add('alphanumeric', False, '')
    mode_items.add('numeric', False, '')
    mode_items.add('binary', False, '')
    mode_items.add('kanji', False, '')

    error_input = inputs.addDropDownCommandInput('error_type', 'Encoding Mode', drop_style)
    error_items = error_input.listItems
    error_items.add('Automatic', True, '')
    error_items.add('L', False, '')
    error_items.add('M', False, '')
    error_items.add('Q', False, '')
    error_items.add('H', False, '')


def add_csv_inputs(inputs: adsk.core.CommandInputs):
    inputs.addStringValueInput('file_name', "File to import", '')

    browse_button = inputs.addBoolValueInput('browse', 'Browse', False, '', False)
    browse_button.isFullWidth = True


# Create file browser dialog box
def browse_for_csv():
    ao = apper.AppObjects()

    file_dialog = ao.ui.createFileDialog()
    file_dialog.initialDirectory = config.app_path
    file_dialog.filter = ".csv files (*.csv)"
    file_dialog.isMultiSelectEnabled = False
    file_dialog.title = 'Select csv file to import'
    dialog_results = file_dialog.showOpen()

    if dialog_results == adsk.core.DialogResults.DialogOK:
        file_names = file_dialog.filenames
        return file_names[0]
    else:
        return ''


class QRCodeMaker(apper.Fusion360CommandBase):
    def __init__(self, name: str, options: dict):
        super().__init__(name, options)
        # self.graphics_group = None
        self.make_preview = True
        self.is_make_qr = options.get('is_make_qr', False)

    def on_input_changed(self, command, inputs, changed_input, input_values):
        self.make_preview = True
        if changed_input.id == 'use_user_size':
            if input_values['use_user_size']:
                inputs.itemById('user_size').isEnabled = True
                inputs.itemById('user_size').isVisible = True
            else:
                inputs.itemById('user_size').isEnabled = False
                inputs.itemById('user_size').isVisible = False
        elif changed_input.id == 'browse':
            changed_input.value = False
            file_name = browse_for_csv()
            if len(file_name) > 0:
                inputs.itemById('file_name').value = file_name

    def on_preview(self, command, inputs, args, input_values):
        if self.make_preview:
            ao = apper.AppObjects()

            qr_data = []
            if self.is_make_qr:
                qr_data = make_qr_from_message(input_values)
            else:
                file_name = input_values['file_name']
                if len(file_name) > 0:
                    qr_data = import_qr_from_file(file_name)

            if len(qr_data) > 0:
                temp_body = get_qr_temp_geometry(qr_data, input_values)

                target_body = get_target_body(input_values['sketch_point'][0])

                # TODO Why is custom graphics so slow?
                make_real_geometry(target_body, temp_body)
                # make_graphics(t_body, self.graphics_group)
                args.isValidResult = True

            self.make_preview = False

    def on_execute(self, command, inputs, args, input_values):
        # sketch_point: adsk.fusion.SketchPoint = input_values['sketch_point'][0]
        # t_body = build_qr(input_values)
        # make_real_geometry(sketch_point.parentSketch.parentComponent, t_body)
        pass

    def on_destroy(self, command, inputs, reason, input_values):
        # clear_graphics(self.graphics_group)
        # self.graphics_group.deleteMe()
        pass

    def on_create(self, command, inputs):
        ao = apper.AppObjects()
        # self.graphics_group = ao.root_comp.customGraphicsGroups.add()
        self.make_preview = True

        default_block_size = adsk.core.ValueInput.createByString(BLOCK)
        default_block_height = adsk.core.ValueInput.createByString(HEIGHT)
        default_base_height = adsk.core.ValueInput.createByString(BASE)
        default_units = ao.units_manager.defaultLengthUnits

        selection_input = inputs.addSelectionInput('sketch_point', "Center Point", "Pick Sketch Point for center")
        selection_input.addSelectionFilter("SketchPoints")

        inputs.addValueInput('block_size', 'QR Block Size', default_units, default_block_size)
        inputs.addValueInput('block_height', 'QR Block Height', default_units, default_block_height)
        inputs.addValueInput('base_height', 'Base Height (Can be zero)', default_units, default_base_height)

        group_input = inputs.addGroupCommandInput('group', 'QR Code Definition')

        if self.is_make_qr:
            add_make_inputs(group_input.children)
        else:
            add_csv_inputs(group_input.children)
