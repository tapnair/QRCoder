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
import adsk.cam
import adsk.core
import adsk.fusion
import traceback

# Defaults (in cm)
BLOCK = 1.0
HEIGHT = 1.0
BASE = .5

# File assumed to be in script root directory
FILE_NAME = 'QR-17x.csv'

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        # ui.messageBox('Hello script')

        file_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), FILE_NAME)
        with open(file_name, newline='') as f:
            reader = csv.reader(f)
            qr_data = list(reader)

        # print(qr_data)

        b_mgr = adsk.fusion.TemporaryBRepManager.get()

        selection = ui.selectEntity("Pick Sketch Point for center", "SketchPoints")
        sketch_point = adsk.fusion.SketchPoint.cast(selection.entity)

        qr_size = len(qr_data)

        middle_point = sketch_point.worldGeometry

        x_dir = sketch_point.parentSketch.xDirection
        x_dir.normalize()
        y_dir = sketch_point.parentSketch.yDirection
        y_dir.normalize()

        start_point = middle_point.copy()
        x_start_move = x_dir.copy()
        x_start_move.scaleBy((.5 * BLOCK) * (1 - qr_size))
        start_point.translateBy(x_start_move)
        y_start_move = y_dir.copy()
        y_start_move.scaleBy((.5 * BLOCK) * (qr_size-1))
        start_point.translateBy(y_start_move)

        size = BLOCK * qr_size
        base_t_box = adsk.core.OrientedBoundingBox3D.create(middle_point, x_dir, y_dir, size, size, BASE)
        base_t_body = b_mgr.createBox(base_t_box)

        component = sketch_point.parentSketch.parentComponent
        base_feature = component.features.baseFeatures.add()
        base_feature.startEdit()

        tools = adsk.core.ObjectCollection.create()

        for i, row in enumerate(qr_data):
            for j, col in enumerate(row):
                if int(col) == 1:
                    c_point = start_point.copy()
                    x_move = x_dir.copy()
                    y_move = y_dir.copy()

                    x_move.scaleBy(j * BLOCK)
                    y_move.scaleBy(-1 * i * BLOCK)

                    c_point.translateBy(x_move)
                    c_point.translateBy(y_move)

                    b_box = adsk.core.OrientedBoundingBox3D.create(c_point, x_dir, y_dir, BLOCK, BLOCK, HEIGHT + BASE)
                    t_body = b_mgr.createBox(b_box)
                    b_mgr.booleanOperation(base_t_body, t_body, adsk.fusion.BooleanTypes.UnionBooleanType)
                    # real_body = component.bRepBodies.add(t_body, base_feature)
                    # tools.add(real_body)

        real_body = component.bRepBodies.add(base_t_body, base_feature)

        base_feature.finishEdit()
        tools.add(base_feature.bodies.item(0))
        
        combine_input = component.features.combineFeatures.createInput(component.bRepBodies.item(0), tools)
        component.features.combineFeatures.add(combine_input)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
