import os
import sys
import time

import numpy as np
import openpyxl
from playsound import playsound
from PIL import Image, ImageOps
from PIL.ImageQt import ImageQt
from PIL import ImageFilter

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QDir, QUrl, Qt, QPoint, QRect, QSize
from PyQt5.QtGui import QPixmap
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QCamera, QCameraInfo
from PyQt5.QtMultimediaWidgets import QVideoWidget, QCameraViewfinder
from PyQt5.QtWidgets import QApplication, QStyle, QFileDialog, QVBoxLayout, QPushButton, QLabel, QWidget, QSlider, \
    QHBoxLayout, QErrorMessage, QCheckBox, QTableWidgetItem, QComboBox, QMessageBox, QRubberBand

from views.imageai_mainwindow_with_chxbx_settings_btn import Ui_MainWindow
from views.settings_widget import Ui_Settings


class SettingsWidget(QtWidgets.QDialog):
    image_path = ''
    width = None
    image_stack = []
    return_image_stack = []
    filters = {'BLUR': False, 'DETAIL': False, 'EDGE_ENHANCE': False, 'EDGE_ENHANCE_MORE': False, 'EMBOSS': False,
               'FIND_EDGES': False, 'SHARPEN': False, 'SMOOTH': False, 'SMOOTH_MORE': False}

    def __init__(self, root, **kwargs):
        super(SettingsWidget, self).__init__(root, **kwargs)
        self.main = root
        self.ui = Ui_Settings()
        self.ui.setupUi(self)
        self.ui.button_apply.clicked.connect(self.apply)
        self.ui.button_undo.clicked.connect(self.undo)
        self.ui.button_return.clicked.connect(self.return_last)
        self.ui.button_undo.setEnabled(False)
        self.ui.button_return.setEnabled(False)
        self.ui.button_save.clicked.connect(self.save_image)

        self.ui.slider_linear_contrast_g_max.setVisible(False)
        self.ui.slider_linear_contrast_g_min.setVisible(False)
        self.ui.slider_small_ogj_solarize.setVisible(False)
        self.ui.slider_large_ogj_binarize.setVisible(False)
        self.ui.slider_large_ogj_prepare_max.setVisible(False)
        self.ui.slider_large_ogj_prepare_min.setVisible(False)

        self.ui.checkBox_linear_contrast.stateChanged.connect(self.linear_contrast_state_changed)
        self.ui.checkBox_small_obj.stateChanged.connect(self.small_obj_state_changed)
        self.ui.checkBox_large_obj.stateChanged.connect(self.large_ogj_state_changed)

    def linear_contrast_state_changed(self, state):
        if state:
            self.ui.slider_linear_contrast_g_max.setVisible(True)
            self.ui.slider_linear_contrast_g_min.setVisible(True)
        else:
            self.ui.slider_linear_contrast_g_max.setVisible(False)
            self.ui.slider_linear_contrast_g_min.setVisible(False)

    def small_obj_state_changed(self, state):
        if state:
            self.ui.slider_small_ogj_solarize.setVisible(True)
            self.ui.slider_small_ogj_prepare_min.setVisible(True)
            self.ui.slider_small_ogj_prepare_max.setVisible(True)
        else:
            self.ui.slider_small_ogj_solarize.setVisible(False)
            self.ui.slider_small_ogj_prepare_min.setVisible(False)
            self.ui.slider_small_ogj_prepare_max.setVisible(False)

    def large_ogj_state_changed(self, state):
        if state:
            self.ui.slider_large_ogj_binarize.setVisible(True)
            self.ui.slider_large_ogj_prepare_max.setVisible(True)
            self.ui.slider_large_ogj_prepare_min.setVisible(True)
        else:
            self.ui.slider_large_ogj_binarize.setVisible(False)
            self.ui.slider_large_ogj_prepare_max.setVisible(False)
            self.ui.slider_large_ogj_prepare_min.setVisible(False)

    def set_gray_image(self):
        im = Image.open(self.image_path)
        im = self.image_stack[-1]
        im_l = im.convert('L')

        self.image_stack.append(im_l)
        self.main.show_image_from_settings(im_l)

    def image_linear_contrast(self):
        # im = Image.open(self.image_path)
        im = self.image_stack[-1]

        im_arr = np.array(im.convert("L"))
        g_min = self.ui.slider_linear_contrast_g_min.value()
        g_max = self.ui.slider_linear_contrast_g_max.value()
        f_max, f_min = np.max(im_arr), np.min(im_arr)
        im_arr = (im_arr - f_min) / (f_max - f_min) * (g_max - g_min) + g_min
        img = Image.fromarray(np.uint8(im_arr))

        # img.show()
        self.image_stack.append(img)
        self.main.show_image_from_settings(img)

    def image_solarize(self, value_solarize):
        print("Соляризация:", value_solarize)
        # im1 = Image.open(self.file_name)
        im = self.image_stack[-1]

        # im_arr = np.array(im.convert("L"))
        # f_max = np.max(im_arr)
        # k = value_solarize / 1000
        # im_arr = k * im_arr * (np.full(im_arr.shape, f_max) - im_arr)
        # im_arr = k * np.dot(im_arr, (np.full(im_arr.shape, f_max) - im_arr))
        # img = Image.fromarray(np.uint8(im_arr))

        k = value_solarize
        im = im.convert('L')
        img = ImageOps.solarize(im, threshold=k)

        self.image_stack.append(img)
        self.main.show_image_from_settings(img)

    def image_binarize(self, value_binarize):
        # image_file = Image.open(self.file_name)
        im = self.image_stack[-1]
        im = im.convert('L')
        im = im.point(lambda p: 255 if p > value_binarize else 0)
        im = im.convert('1')

        self.image_stack.append(im)
        self.main.show_image_from_settings(im)

    def f(self, x, x0, x1):
        y0, y1 = 0, 255
        if x < x0 or x > x1:
            return 0
        else:
            y = (x - x0) * (y1 - y0) / (x1 - x0) + y0
            return y

    def image_prepare(self, val_prep_min, val_prep_max):
        im = self.image_stack[-1]
        print("Image prepare values:", val_prep_min, val_prep_max)
        im = im.convert('L')
        im = im.point(lambda p: self.f(p, val_prep_min, val_prep_max))
        # im = im.convert('1')

        self.image_stack.append(im)
        self.main.show_image_from_settings(im)
        # im.show()

    def image_blur(self, blur_value):
        im = self.image_stack[-1]
        img = im.filter(ImageFilter.BoxBlur(blur_value))
        self.image_stack.append(img)
        self.main.show_image_from_settings(img)

    def image_emboss(self, state):
        if state:
            im = self.image_stack[-1]
            img = im.filter(ImageFilter.EMBOSS)
            self.image_stack.append(img)
            self.main.show_image_from_settings(img)

    def image_sharpen(self, state):
        if state:
            im = self.image_stack[-1]
            img = im.filter(ImageFilter.SHARPEN)
            self.image_stack.append(img)
            self.main.show_image_from_settings(img)

    def image_find_edges(self, state):
        if state:
            im = self.image_stack[-1]
            img = im.filter(ImageFilter.FIND_EDGES)
            self.image_stack.append(img)
            self.main.show_image_from_settings(img)

    def image_filter(self):
        im = self.image_stack[-1]
        i = 0
        if self.ui.checkBox_blur.isChecked():
            im = im.filter(ImageFilter.BLUR)
            i += 1
        if self.ui.checkBox_contour.isChecked():
            im = im.filter(ImageFilter.CONTOUR)
            i += 1
        if self.ui.checkBox_detail.isChecked():
            im = im.filter(ImageFilter.DETAIL)
            i += 1
        if self.ui.checkBox_edhe_enhance.isChecked():
            im = im.filter(ImageFilter.EDGE_ENHANCE)
            i += 1
        if self.ui.checkBox_edge_enhance_more.isChecked():
            im = im.filter(ImageFilter.EDGE_ENHANCE_MORE)
            i += 1
        if self.ui.checkBox_emboss.isChecked():
            im = im.filter(ImageFilter.EMBOSS)
            i += 1
        if self.ui.checkBox_find_edges.isChecked():
            im = im.filter(ImageFilter.FIND_EDGES)
            i += 1
        if self.ui.checkBox_sharpen.isChecked():
            im = im.filter(ImageFilter.SHARPEN)
            i += 1
        if self.ui.checkBox_smooth.isChecked():
            im = im.filter(ImageFilter.SMOOTH)
            i += 1
        if self.ui.checkBox_smooth_more.isChecked():
            im = im.filter(ImageFilter.SMOOTH_MORE)
            i += 1

        if i >= 1:
            self.image_stack.append(im)
            self.main.show_image_from_settings(im)

    def apply(self):
        try:
            if self.ui.checkBox_gray.isChecked():
                self.set_gray_image()
            else:
                self.main.set_rgb_image()

            if self.ui.checkBox_linear_contrast.isChecked():
                self.image_linear_contrast()

            if self.ui.checkBox_large_obj.isChecked():
                value_binarize = self.ui.slider_large_ogj_binarize.value()
                value_prepare_max = self.ui.slider_large_ogj_prepare_max.value()
                value_prepare_min = self.ui.slider_large_ogj_prepare_min.value()
                if value_binarize != 0:
                    self.image_binarize(value_binarize)
                if (value_prepare_max - value_prepare_min) > 0:
                    self.image_prepare(value_prepare_min, value_prepare_max)

            if self.ui.checkBox_small_obj.isChecked():
                value_solarize = self.ui.slider_small_ogj_solarize.value()
                value_prepare_min = self.ui.slider_small_ogj_prepare_min.value()
                value_prepare_max = self.ui.slider_small_ogj_prepare_max.value()
                self.image_solarize(value_solarize)
                self.image_prepare(value_prepare_min, value_prepare_max)

            self.image_filter()

            if len(self.image_stack) > 5:
                self.image_stack.pop(0)
                # self.main.show_image_from_settings(self.image_stack[-1])
            self.ui.button_undo.setEnabled(True)
            print(len(self.image_stack))
        except UnboundLocalError as err:
            print(err)
            print("Error!")
            self.close()

    def undo(self):
        """
        При нажатии на кнопку "Undo" примененный фильтр отменится
        и изображение вернется в предыдущее состояние
        :return:
        """
        if len(self.image_stack) > 1:
            return_image = self.image_stack.pop(-1)
            self.return_image_stack.append(return_image)
            self.main.show_image_from_settings(self.image_stack[-1])
            self.ui.button_return.setEnabled(True)
        else:
            self.ui.button_undo.setEnabled(False)
        print(len(self.image_stack))

    def return_last(self):
        """
        После нажатии на кнопку "Undo" нажатие на кнопку "Return"
        позволяет отменить возрат.
        :return:
        """
        self.image_stack.append(self.return_image_stack[-1])
        self.main.show_image_from_settings(self.image_stack[-1])
        self.return_image_stack.clear()
        print(len(self.image_stack))
        if len(self.return_image_stack) == 0:
            self.ui.button_return.setEnabled(False)

    def save_image(self):
        self.main.save_image(self.image_stack[-1])

class MyWindow(QtWidgets.QMainWindow):
    file_name = ''
    layout = QVBoxLayout()
    objects_for_detect = []

    checked_list = []
    signs = []
    counts = []
    image_crop_state = []
    image_crop_return = []

    def __init__(self):
        super(MyWindow, self).__init__()
        self.controlLayout_1 = QHBoxLayout()
        self.controlLayout_2 = QHBoxLayout()
        self.mediaPlayer_1 = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.mediaPlayer_2 = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.play_button_1 = QPushButton()
        self.play_button_2 = QPushButton()
        self.positionSlider_1 = QSlider(Qt.Horizontal)
        self.positionSlider_2 = QSlider(Qt.Horizontal)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.settings_window = SettingsWidget(self)

        self.ui.button_setting.clicked.connect(self.settings)
        self.ui.button_browse.clicked.connect(self.open)
        self.ui.button_processing.clicked.connect(self.process)
        self.ui.button_undo_crop.setVisible(False)
        self.ui.button_return_crop.setVisible(False)
        self.ui.button_undo_crop.clicked.connect(self.undo_crop_image)

        self.ui.tableWidget_check.setVisible(False)
        self.ui.comboBox_detect_obj.currentIndexChanged.connect(self.combo_box_changed)

        self.ui.tableWidget_check.setColumnCount(4)
        self.ui.tableWidget_check.setHorizontalHeaderLabels(["Objects", "Check", "Sign", "Count"])
        header = self.ui.tableWidget_check.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)

    def combo_box_changed(self, value):
        """
            Функция заполняет таблицу данными из excel-файла.
        :param value: позиция ComboBox
        :return:
        """
        if value == 0:
            self.ui.tableWidget_check.setVisible(False)
        else:
            self.ui.tableWidget_check.setVisible(True)
            self.ui.tableWidget_check.setRowCount(80)
            # открываем файл со списком объектов и помещаем список в tableWidget_check
            book = openpyxl.open("inputs/objects.xlsx", read_only=True)
            sheet = book.active

            for row in range(80):
                widget = QWidget()
                checkbox = QCheckBox()
                checkbox.setCheckState(Qt.Unchecked)
                layoutH = QHBoxLayout(widget)
                layoutH.addWidget(checkbox)
                layoutH.setAlignment(Qt.AlignCenter)
                layoutH.setContentsMargins(0, 0, 0, 0)

                self.ui.tableWidget_check.setCellWidget(row, 1, widget)
                centralWidget = QWidget()

                combo = QComboBox()
                combo.addItems([">", "<", "="])
                layout = QVBoxLayout(centralWidget)
                layout.addWidget(combo)
                self.ui.tableWidget_check.setCellWidget(row, 2, centralWidget)
                self.ui.tableWidget_check.setItem(row, 0, QTableWidgetItem(str(sheet[row + 1][0].value)))
                # self.objects_for_detect.append(str(sheet[row + 1][0].value))
            # print(self.objects_for_detect)

    def show_video(self, media_player: QMediaPlayer, layout: QVBoxLayout, control_layout: QHBoxLayout,
                   button: QPushButton, position_slider: QSlider, file_name):
        """
            Функция прикрепляет media_player, video_widget, buuton,
            position_slider соответвующему layout("окошко" слева
            или справа в зависимости от момента вызова функции в коде,
            в данном случае нажатие кнопки "Browse" вставляет видео в левое окошко,
            а нажатие кнопки "Обработать" вставляет в правое окошко).
        :param media_player:
        :param layout:
        :param control_layout:
        :param button: Кнопка запуска/остановки
        :param position_slider:
        :param file_name: Путь к файлу,который был выбран после нажатие на кнопку "Browse"
        :return:
        """
        delete_items_of_layout(layout)

        video_widget = QVideoWidget()

        button.clicked.connect(lambda: self.play(media_player))
        button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))

        position_slider.setRange(0, 0)
        position_slider.sliderMoved.connect(lambda: self.setPosition(media_player, position_slider.sliderPosition()))

        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.addWidget(button)
        control_layout.addWidget(position_slider)

        layout.addWidget(video_widget)
        layout.addLayout(control_layout)

        media_player.setVideoOutput(video_widget)
        media_player.setMedia(QMediaContent(QUrl.fromLocalFile(file_name)))
        media_player.play()
        media_player.setNotifyInterval(10)
        media_player.stateChanged.connect(lambda: self.mediaStateChanged(media_player, button, media_player.state()))
        media_player.positionChanged.connect(lambda: self.positionChanged(position_slider, media_player.position()))
        media_player.durationChanged.connect(lambda: self.durationChanged(position_slider, media_player.duration()))

    def show_photo(self, layout: QVBoxLayout, control_layout: QHBoxLayout, width: int, file_name):
        """
            Функция прикрепляет фото соответвующему layout("окошко" слева
            или справа в зависимости от момента вызова функции в коде,
            в данном случае нажатие кнопки "Browse" вставляет видео в левое окошко,
            а нажатие кнопки "Обработать" вставляет в правое окошко).
        :param layout:
        :param control_layout:
        :param width: Ширина layout для уменшения размера исходного изображения
        :param file_name: Путь к файлу,который был выбран после нажатие на кнопку "Browse"
        :return:
        """
        self.box_delete(layout, control_layout)
        delete_items_of_layout(layout)
        if type(file_name) == str:
            pixmap = QPixmap(file_name)
        else:
            pixmap = file_name
        self.image_crop_state.append(pixmap)
        print(len(self.image_crop_state))

        pixmap = pixmap.scaledToWidth(width)

        label = QLabel(self)
        label.setPixmap(pixmap)
        layout.addWidget(label)

        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self.ui.verticalLayout.itemAt(0).widget())
        self.origin = QPoint()

    def show_camera_stream(self, media_player: QMediaPlayer, layout: QVBoxLayout, control_layout: QHBoxLayout,
                           button: QPushButton, position_slider: QSlider, file_name):
        self.online_webcams = QCameraInfo.availableCameras()
        if not self.online_webcams:
            pass
        self.camera = QCameraViewfinder()
        self.ui.verticalLayout.addWidget(self.camera)
        self.camera.show()
        self.get_webcam(0)
        self.ui.button_processing.setEnabled(True)

    def open(self):
        """
            Функция нажатия на кнопку "Browse". В зависимости от
            значения self.ui.comboBox_modes будут доступны разные форматы:
            Videos (*.mp4 *avi) если 0,
            Images (*.png *.jpg) если 1,
            иначе запускается доступная камера.
        """
        self.ui.button_setting.setEnabled(True)

        if self.ui.comboBox_modes.currentIndex() == 0:
            file_name, _ = QFileDialog.getOpenFileName(self, "Open Movie",
                                                       QDir.homePath() + "/PycharmProjects/image_analysis_project/",
                                                       "Videos (*.mp4 *avi)")
            print(file_name)
            if file_name != '':
                self.show_video(self.mediaPlayer_1, self.ui.verticalLayout, self.controlLayout_1, self.play_button_1,
                                self.positionSlider_1, file_name)
                self.ui.button_processing.setEnabled(True)
                self.file_name = file_name
        elif self.ui.comboBox_modes.currentIndex() == 1:
            file_name, _ = QFileDialog.getOpenFileName(self, "Open Photo",
                                                       QDir.homePath() + "/PycharmProjects/image_analysis_project/",
                                                       "Images (*.png *.jpg *.jpeg)")
            print(file_name)
            if file_name != '':
                self.show_photo(self.ui.verticalLayout, self.controlLayout_1, self.ui.verticalLayoutWidget.width(),
                                file_name)
                self.ui.button_processing.setEnabled(True)
                self.file_name = file_name
                self.ui.button_undo_crop.setVisible(True)
                self.ui.button_return_crop.setVisible(True)
        else:
            # pass
            # self.online_webcams = QCameraInfo.availableCameras()
            # if not self.online_webcams:
            #     pass
            # self.camera = QCameraViewfinder()
            # self.ui.verticalLayout.addWidget(self.camera)
            # self.camera.show()
            # self.get_webcam(0)
            self.ui.button_processing.setEnabled(True)

    def get_webcam(self, i):
        self.my_webcam = QCamera(self.online_webcams[i])
        self.my_webcam.setViewfinder(self.camera)
        self.my_webcam.setCaptureMode(QCamera.CaptureStillImage)
        self.my_webcam.error.connect(lambda: self.alert(self.my_webcam.errorString()))
        self.my_webcam.start()

    def play(self, media_player: QMediaPlayer):
        """
            Функция срабатывает при нажатии кнопки
            запуска/остановки во время проигрывания видео.
        """
        if media_player.state() == QMediaPlayer.PlayingState:
            media_player.pause()
        else:
            media_player.play()

    def mediaStateChanged(self, media_player: QMediaPlayer, play_button: QPushButton, state):
        if media_player.state() == QMediaPlayer.PlayingState:
            play_button.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            play_button.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPlay))

    def positionChanged(self, position_slider: QSlider, position):
        position_slider.setValue(position)

    def durationChanged(self, position_slider: QSlider, duration):
        position_slider.setRange(0, duration)

    def setPosition(self, media_player: QMediaPlayer, position):
        media_player.setPosition(position)

    def process(self):
        """
            Функция срабатывает при нажатии на кнопку "Обработать".
            Запускает процесс распознавания объектов в зависимости от задачи,
            после выводит результат в "окошко" справа.
        """
        print(self.file_name)
        if (os.path.splitext(self.file_name)[1][1:] == "mp4" or os.path.splitext(self.file_name)[1][1:] == "avi"):
            file_name_output = ''
            min_probab = int(self.ui.edit_line_min_percent_probab.text())
            self.table_init(3, ["Objects", "Count", "Frame"])
            if self.ui.comboBox_detect_obj.currentIndex() == 0:
                file_name_output = self.video_process(self.file_name, min_probab)
            else:
                self.checked_list = []
                self.signs = []
                self.counts = []
                for i in range(self.ui.tableWidget_check.rowCount()):
                    if self.ui.tableWidget_check.cellWidget(i, 1).findChild(type(QCheckBox())).isChecked():
                        self.checked_list.append(self.ui.tableWidget_check.item(i, 0).text())
                        self.signs.append(
                            str(self.ui.tableWidget_check.cellWidget(i, 2).findChild(type(QComboBox())).currentText()))
                        self.counts.append(self.ui.tableWidget_check.item(i, 3).text())
                print(self.checked_list)
                if self.checked_list:
                    file_name_output = self.video_process(self.file_name, min_probab, self.checked_list)
                else:
                    show_message_box("Выберите объекты для распознавания!")

            # file_name_output = '/home/ilnar/PycharmProjects/image_analysis_project/results/street_detected.avi'
            if file_name_output:
                self.show_video(self.mediaPlayer_2, self.ui.verticalLayout_2, self.controlLayout_2, self.play_button_2,
                                self.positionSlider_2, file_name_output)

        elif (os.path.splitext(self.file_name)[1][1:] == "jpg" or os.path.splitext(self.file_name)[1][1:] == "png"):
            min_probab = int(self.ui.edit_line_min_percent_probab.text())
            self.table_init(2, ["Objects", "Count"])
            if self.ui.comboBox_detect_obj.currentIndex() == 0:
                file_name_output = self.image_process(self.file_name, min_probab)
            else:
                self.checked_list = []
                self.signs = []
                self.counts = []
                for i in range(self.ui.tableWidget_check.rowCount()):
                    if self.ui.tableWidget_check.cellWidget(i, 1).findChild(type(QCheckBox())).isChecked():
                        self.checked_list.append(self.ui.tableWidget_check.item(i, 0).text())
                        self.signs.append(
                            str(self.ui.tableWidget_check.cellWidget(i, 2).findChild(type(QComboBox())).currentText()))
                        self.counts.append(self.ui.tableWidget_check.item(i, 3).text())
                print(self.checked_list)
                file_name_output = self.image_process(self.file_name, min_probab, self.checked_list)
            if file_name_output:
                self.show_photo(self.ui.verticalLayout_2, self.controlLayout_2, self.ui.verticalLayoutWidget_2.width(),
                                file_name_output)
        else:
            min_probab = int(self.ui.edit_line_min_percent_probab.text())
            self.table_init(3, ["Objects", "Count", "Time"])
            if self.ui.comboBox_detect_obj.currentIndex() == 0:
                self.camera_processing(min_probab)
            else:
                self.checked_list = []
                for i in range(self.ui.tableWidget_check.rowCount()):
                    if self.ui.tableWidget_check.cellWidget(i, 1).findChild(type(QCheckBox())).isChecked():
                        self.checked_list.append(self.ui.tableWidget_check.item(i, 0).text())
                        self.signs.append(
                            str(self.ui.tableWidget_check.cellWidget(i, 2).findChild(type(QComboBox())).currentText()))
                        self.counts.append(self.ui.tableWidget_check.item(i, 3).text())
                print(self.checked_list)
                if self.checked_list:
                    self.camera_processing(min_probab, self.checked_list)
                else:
                    show_message_box("Выберите объекты для распознавания!")

    def video_process(self, file_name, min_probab_precent, checked_list=None):
        from imageai.Detection import VideoObjectDetection

        execution_path = os.getcwd()

        detector = VideoObjectDetection()
        detector.setModelTypeAsRetinaNet()
        detector.setModelPath(os.path.join(execution_path, "models/resnet50_coco_best_v2.1.0.h5"))
        detector.loadModel(detection_speed="flash")

        custom_objects = detector.CustomObjects()
        if not checked_list:
            keys = get_json_keys(custom_objects)
            for key in keys:
                custom_objects[key] = 'valid'
        else:
            for r in checked_list:
                custom_objects[str(r)] = 'valid'

        video_path = detector.detectObjectsFromVideo(
            custom_objects=custom_objects,
            input_file_path=file_name,
            output_file_path=os.path.join(execution_path, "results/street_detected"),
            frames_per_second=20, log_progress=True,
            per_frame_function=self.video_frame_process,
            # video_complete_function=video_process_complete,
            frame_detection_interval=3,
            minimum_percentage_probability=min_probab_precent)
        print(video_path)
        return video_path

    def video_frame_process(self, frame_position, objects_array, objects_count):
        """
            Функция срабатывает после обработки кадра и
            заполняет таблицу данными:
                название объекта,
                их количество в данном кадре,
                номер кадра.
        :param frame_position: номер кадра.
        :param objects_array: массив объектов.
        :param objects_count: количество объектов
        """
        print(frame_position)
        print(objects_array)
        print(objects_count)
        if self.checked_list:
            row_position = self.ui.tableWidget.rowCount()
            self.ui.tableWidget.insertRow(row_position)
            keys = get_json_keys(objects_count)
            for i in range(len(objects_count)):
                self.ui.tableWidget.setItem(row_position, 0, QtWidgets.QTableWidgetItem(keys[i]))
                self.ui.tableWidget.setItem(row_position, 1, QtWidgets.QTableWidgetItem(str(objects_count[keys[i]])))
                self.ui.tableWidget.setItem(row_position, 2, QtWidgets.QTableWidgetItem(str(frame_position)))
            self.process_rules(objects_count, keys)

    def image_process(self, file_name, min_probab_precent, checked_list=None):
        from imageai.Detection import ObjectDetection

        execution_path = os.getcwd()
        output_file = os.path.join(execution_path, "results/object3_detected.jpg")

        detector = ObjectDetection()
        detector.setModelTypeAsYOLOv3()
        detector.setModelPath(os.path.join(execution_path, "models/yolo.h5"))
        detector.loadModel()

        custom_objects = detector.CustomObjects()
        if not checked_list:
            print('Checked list is None:', checked_list)
            keys = get_json_keys(custom_objects)
            for key in keys:
                custom_objects[key] = 'valid'
            print(custom_objects)
        else:
            print('Checked list is not None:', checked_list)
            for r in checked_list:
                custom_objects[str(r)] = 'valid'
            print(custom_objects)

        detections = detector.detectObjectsFromImage(input_image=os.path.join(execution_path, file_name),
                                                     output_image_path=output_file,
                                                     minimum_percentage_probability=min_probab_precent,
                                                     custom_objects=custom_objects)

        objects_dictionary = get_objects_count(detections)
        print(objects_dictionary)
        if objects_dictionary:
            self.after_image_process(objects_dictionary)
            print("Hi!")
            return output_file
        else:
            show_message_box("Объекты не найдены!")
            return None

    def after_image_process(self, objects_dictionary):
        """
            Функция получает список распознанных
             объектов и заполняет таблицу
        :param objects_dictionary:
        :return:
        """
        keys = get_json_keys(objects_dictionary)
        print(keys)
        for i in range(len(keys)):
            row_position = self.ui.tableWidget.rowCount()
            self.ui.tableWidget.insertRow(row_position)
            self.ui.tableWidget.setItem(row_position, 0, QtWidgets.QTableWidgetItem(keys[i]))
            self.ui.tableWidget.setItem(row_position, 1, QtWidgets.QTableWidgetItem(str(objects_dictionary[keys[i]])))
        self.process_rules(objects_dictionary, keys)

    def camera_processing(self, min_probab_precent, checked_list=None):
        """
            Функция открывает новое окно, в котором
            отображается видео с камеры с распознанными объектами,
            и заполняет таблицу данными:
                название объекта,
                его количество в кадре,
                дата и время распознавания.
        :param min_probab_precent: минимальный процент точности распознавания.
        """
        import cv2
        from imageai.Detection import ObjectDetection

        execution_path = os.getcwd()

        cv2.destroyAllWindows()
        camera = cv2.VideoCapture(0)
        detector = ObjectDetection()
        detector.setModelTypeAsYOLOv3()
        detector.setModelPath(os.path.join(execution_path, "models/yolo.h5"))
        detector.loadModel(detection_speed="flash")

        custom_objects = detector.CustomObjects()
        if not checked_list:
            keys = get_json_keys(custom_objects)
            for key in keys:
                custom_objects[key] = 'valid'
        else:
            for r in checked_list:
                custom_objects[str(r)] = 'valid'

        while camera.isOpened():
            ret, frame = camera.read()
            start = time.time()

            # frame = self.camera_frame_filtering(frame)
            _, array_detection = detector.detectObjectsFromImage(input_image=frame,
                                                                 input_type="array",
                                                                 output_type="array",
                                                                 minimum_percentage_probability=min_probab_precent,
                                                                 custom_objects=custom_objects)
            print(array_detection)

            objects_dictionary = get_objects_count(array_detection)
            print(objects_dictionary)
            keys = get_json_keys(objects_dictionary)
            if keys:
                row_position = self.ui.tableWidget.rowCount()
                self.ui.tableWidget.insertRow(row_position)
                for i in range(len(objects_dictionary)):
                    self.ui.tableWidget.setItem(row_position, 0, QtWidgets.QTableWidgetItem(keys[i]))
                    self.ui.tableWidget.setItem(row_position, 1,
                                                QtWidgets.QTableWidgetItem(str(objects_dictionary[keys[i]])))
                    self.ui.tableWidget.setItem(row_position, 2, QtWidgets.QTableWidgetItem(time.ctime(start)))
                self.process_rules(objects_dictionary, keys)

                for obj in array_detection:
                    coord = obj['box_points']
                    cv2.rectangle(frame, (coord[0], coord[1], coord[2], coord[3]), (0, 0, 255))
                    cv2.putText(frame, obj['name'], (coord[0], coord[1] - 6),
                                cv2.FONT_HERSHEY_DUPLEX, 1.0,
                                (255, 255, 255))
                    cv2.putText(frame, str(obj[('percentage_probability')]), (coord[0] + 120, coord[1] - 6),
                                cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255))
            cv2.imshow('Camera', frame)
            if cv2.waitKey(25) & 0xFF == ord('q'):
                break
        camera.release()
        cv2.destroyAllWindows()

    def table_init(self, columns_count, headers):
        self.ui.tableWidget.setColumnCount(columns_count)
        self.ui.tableWidget.setHorizontalHeaderLabels(headers)
        header = self.ui.tableWidget.horizontalHeader()
        # header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        for i in range(columns_count):
            header.setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeToContents)

    def box_delete(self, layout: QVBoxLayout, box):
        """
            Функция удаляет элементы с layout.
            Работает вместе с delete_items_of_layout(layout).
            Это позволяет полностью очистить layout.
        """
        for i in range(layout.count()):
            layout_item = layout.itemAt(i)
            if layout_item.layout() == box:
                delete_items_of_layout(layout_item.layout())
                layout.removeItem(layout_item)
                break

    def alert(self, s):
        """
            Выводит все ошибки в отдельное окно.
        """
        err = QErrorMessage(self)
        err.showMessage(s)

    def process_rules(self, objects_dictionary, keys):
        """
            Функция, которая проверяет правила ['>', '<', '='] из tableWidget_check.
            Если условия не выполняются, то прозвучит сигнал и объект в таблице окрасится в красный.
        :return:
        """
        print("-" * 40)
        print(self.checked_list, ":", self.signs, ";", self.counts, "\n", objects_dictionary)
        print("-" * 40)
        self.objects_for_detect.append(objects_dictionary)
        print(self.objects_for_detect)
        for i in range(len(self.checked_list)):
            if self.signs[i] == "<":
                for s in range(len(self.objects_for_detect)):
                    if list(self.objects_for_detect[s])[0] == self.checked_list[i] and (
                            int(objects_dictionary[self.checked_list[i]]) < int(self.counts[i])):
                        print("beep" + " " + str(self.checked_list[i]))
                        self.ui.tableWidget.item(s, 0).setBackground(QtGui.QColor(255, 0, 0))
                    playsound('inputs/sound.wav')
            elif self.signs[i] == ">":
                if (int(objects_dictionary[self.checked_list[i]]) > int(self.counts[i])):
                    print("beep" + " " + str(self.checked_list[i]))
                    for s in range(len(self.objects_for_detect)):
                        if list(self.objects_for_detect[s])[0] == self.checked_list[i]:
                            self.ui.tableWidget.item(s, 0).setBackground(QtGui.QColor(255, 0, 0))
                    playsound('inputs/sound.wav')
            else:
                if (int(objects_dictionary[self.checked_list[i]]) == int(self.counts[i])):
                    print("beep" + " " + str(self.checked_list[i]))
                    for s in range(len(self.objects_for_detect)):
                        if list(self.objects_for_detect[s])[0] == self.checked_list[i]:
                            self.ui.tableWidget.item(s, 0).setBackground(QtGui.QColor(255, 0, 0))
                    playsound('inputs/sound.wav')

    def settings(self, checked):
        if self.ui.comboBox_modes.currentIndex() == 1:
            try:
                self.settings_window.image_path = self.file_name
                self.settings_window.image_stack.append(Image.open(self.file_name))
                if self.settings_window.isVisible():
                    self.settings_window.hide()
                else:
                    self.settings_window.show()
            except AttributeError:
                show_message_box("Выберите изображение!")
        elif self.ui.comboBox_modes.currentIndex() == 2:
            if self.settings_window.isVisible():
                self.settings_window.hide()
            else:
                self.settings_window.show()

    def show_image_from_settings(self, image):
        qim = ImageQt(image)
        pixmap = QtGui.QPixmap.fromImage(qim)

        self.show_photo(self.ui.verticalLayout, self.controlLayout_1, self.ui.verticalLayoutWidget.width(),
                        pixmap)

    def save_image(self, image):
        qim = ImageQt(image)
        pixmap = QtGui.QPixmap.fromImage(qim)
        file_ar = self.file_name.split('.')
        filtered_image_path = file_ar[0] + "_f." + file_ar[1]
        print(filtered_image_path)
        image_is_saved = pixmap.save(filtered_image_path)
        print(image_is_saved)
        self.file_name = filtered_image_path
        self.show_photo(self.ui.verticalLayout, self.controlLayout_1, self.ui.verticalLayoutWidget.width(),
                        pixmap)

    def set_rgb_image(self):
        self.show_photo(self.ui.verticalLayout, self.controlLayout_1, self.ui.verticalLayoutWidget.width(),
                        self.file_name)

    def camera_frame_filtering(self, frame):
        import cv2

        frame_filt = frame
        if self.settings_window.ui.checkBox_gray.isChecked():
            frame_filt = cv2.cvtColor(frame_filt, cv2.COLOR_BGR2GRAY)
        if self.settings_window.ui.checkBox_blur.isChecked():
            frame_filt = cv2.GaussianBlur(frame_filt, (5, 5), 0)
        if self.settings_window.ui.checkBox_find_edges.isChecked():
            frame_filt = cv2.Canny(frame_filt, 10, 70)
        return frame_filt

    def mousePressEvent(self, event):
        # функция нажатия на кнопку мыши
        if event.button() == Qt.LeftButton:
            self.origin = QPoint(event.pos())
            self.left_top = event.pos()
            print(event.pos())
            self.rubberBand.setGeometry(QRect(self.origin, QSize()))
            self.rubberBand.show()

    def mouseMoveEvent(self, event):
        # Функция движения курсора мышки
        if not self.origin.isNull():
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        # функция отпускания нажатия на кнопку мыши
        if event.button() == Qt.LeftButton:
            self.rubberBand.hide()
        self.right_bottom = event.pos()
        currentRect = self.rubberBand.geometry()
        self.rubberBand.deleteLater()
        cropQPixmap = self.ui.verticalLayout.itemAt(0).widget().pixmap().copy(currentRect)

        self.file_name = 'inputs/cropped_image.png'
        cropQPixmap.save(self.file_name)

        self.show_photo(self.ui.verticalLayout, self.controlLayout_1, self.ui.verticalLayoutWidget.width(),
                        self.file_name)

    def undo_crop_image(self):
        """
        При нажатии на кнопку "Undo" примененный фильтр отменится
        и изображение вернется в предыдущее состояние
        :return:
        """
        if len(self.image_crop_state) > 1:
            image_return = self.image_crop_state.pop()
            pixmap = self.image_crop_state[-1]
            self.show_photo(self.ui.verticalLayout, self.controlLayout_1, self.ui.verticalLayoutWidget.width(),
                            pixmap)
            self.image_crop_return.append(image_return)
            self.ui.button_return_crop.setEnabled(True)
        else:
            self.ui.button_undo_crop.setEnabled(False)

    def return_crop_image(self):
        """
        После нажатии на кнопку "Undo" нажатие на кнопку "Return"
        позволяет отменить возрат.
        :return:
        """
        self.image_stack.append(self.image_crop_return[-1])
        self.main.show_image_from_settings(self.image_crop_state[-1])
        self.return_image_stack.clear()
        print(len(self.image_stack))
        if len(self.return_image_stack) == 0:
            self.ui.button_return_crop.setEnabled(False)


def show_message_box(message):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setText("Предупреждение.")
    msg.setInformativeText(message)
    msg.setWindowTitle("Предупреждение")
    msg.exec_()


def get_objects_count(detections):
    objects_dictionary = dict()
    for obj in detections:
        if obj['name'] in objects_dictionary:
            objects_dictionary[obj['name']] = objects_dictionary.get(obj['name']) + 1
        else:
            objects_dictionary[obj['name']] = 1
    return objects_dictionary


def delete_items_of_layout(layout):
    """
        Удаляет с layout все widget-ы
    """
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
            else:
                delete_items_of_layout(item.layout())


def get_json_keys(data):
    result = []
    for key in data.keys():
        if type(data[key]) != dict:
            result.append(key)
        else:
            result += get_json_keys(data[key])
    return result


def initialize():
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    app.exec_()


if __name__ == '__main__':
    initialize()
