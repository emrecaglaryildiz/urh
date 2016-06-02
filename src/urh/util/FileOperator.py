import os
import shutil
import tarfile
import tempfile
import wave
import zipfile

from PyQt5.QtCore import QDir
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from urh.cythonext.signalFunctions import Symbol

from urh.signalprocessing.LabelSet import LabelSet
from urh.signalprocessing.ProtocoLabel import ProtocolLabel
from urh.signalprocessing.ProtocolBlock import ProtocolBlock
from urh.util.Errors import Errors

VIEW_TYPES = ["Bits", "Hex", "ASCII"]

archives = {}
""":type: dict of [str, str]
   :param: archives[extracted_filename] = filename"""

RECENT_PATH = QDir.homePath()

def uncompress_archives(filenames, temp_dir):
    """
    Extrahiert jedes Archiv aus der Liste von Dateinamen,
    normale Dateien bleiben unverändert.
    Fügt außerdem alle Dateien zu den Recent Files hinzu
    :type filenames: list of str
    :type temp_dir: str
    :rtype: list of str
    """
    fileNames = []
    for filename in filenames:
        if filename.endswith(".tar") or filename.endswith(".tar.gz") or filename.endswith(".tar.bz2"):
            obj = tarfile.open(filename, "r")
            extracted_filenames = []
            for j, member in enumerate(obj.getmembers()):
                obj.extract(member, temp_dir)
                extracted_filename = os.path.join(temp_dir, obj.getnames()[j])
                extracted_filenames.append(extracted_filename)
                archives[extracted_filename] = filename
            fileNames.extend(extracted_filenames[:])
        elif filename.endswith(".zip"):
            obj = zipfile.ZipFile(filename)
            extracted_filenames = []
            for j, info in enumerate(obj.infolist()):
                obj.extract(info, path=temp_dir)
                extracted_filename = os.path.join(temp_dir, obj.namelist()[j])
                extracted_filenames.append(extracted_filename)
                archives[extracted_filename] = filename
            fileNames.extend(extracted_filenames[:])
        else:
            fileNames.append(filename)

    return fileNames


def get_save_file_name(initial_name: str, wav_only=False, parent=None, caption="Save signal"):
    global RECENT_PATH
    if caption == "Save signal":
        filter = "Complex files (*.complex);;Compressed complex files (*.coco);;wav files (*.wav);;all files (*)"
        if wav_only:
            filter = "wav files (*.wav);;all files (*)"
    elif caption == "Save fuzz profile":
        filter = "Fuzzfiles (*.fuzz);;All files (*)"
    else:
        filter = "Protocols (*.proto);;All files (*)"

    filename = None
    dialog = QFileDialog()
    dialog.setFileMode(QFileDialog.AnyFile)
    dialog.setNameFilter(filter)
    dialog.setViewMode(QFileDialog.Detail)
    dialog.setDirectory(RECENT_PATH)
    dialog.setLabelText(QFileDialog.Accept, "Save")
    dialog.setWindowTitle(caption)
    dialog.setAcceptMode(QFileDialog.AcceptSave)
    dialog.selectFile(initial_name)

    if (dialog.exec()):
        filename = dialog.selectedFiles()[0]
        filter = dialog.selectedNameFilter()
        ext = filter[filter.index('*'):filter.index(')')][1:]
        if not os.path.exists(filename) and len(ext) > 0 and not filename.endswith(ext):
            filename += ext

    if filename:
        RECENT_PATH = os.path.split(filename)[0]

    return filename


def save_data_dialog(signalname: str, data, wav_only=False, parent=None) -> str:
    filename = get_save_file_name(signalname, wav_only, parent)

    if filename:
        try:
            save_data(data, filename)
        except Exception as e:
            QMessageBox.critical(parent, "Error saving signal", e.args[0])
            filename = None
    else:
        filename = None

    return filename

def save_data(data, filename: str):
    if filename.endswith(".wav"):
        f = wave.open(filename, "w")
        f.setnchannels(1)
        f.setsampwidth(1)
        f.setframerate(1000000)
        f.writeframes(data)
        f.my_close()
    elif filename.endswith(".coco"):
        with tarfile.open(filename, 'w:bz2') as tarwrite:
            tmp_name = os.path.join(QDir.tempPath(), "tmpfile")
            data.tofile(tmp_name)
            tarwrite.add(tmp_name)
        os.remove(tmp_name)
    else:
        try:
            data.tofile(filename)
        except Exception as e:
            Errors.write_error(e)

    if filename in archives.keys():
        archive = archives[filename]
        if archive.endswith("zip"):
            rewrite_zip(archive)
        elif archive.endswith("tar") or archive.endswith("bz2") or archive.endswith("gz"):
            rewrite_tar(archive)


def save_signal(signal):
    filename = signal.filename
    data = signal.data if not filename.endswith(".wav") else signal.wave_data
    save_data(data, filename)

def rewrite_zip(zipfname):
    tempdir = tempfile.mkdtemp()
    try:
        tempname = os.path.join(tempdir, 'new.zip')
        files_in_archive = [f for f in archives.keys() if archives[f] == zipfname]
        with zipfile.ZipFile(tempname, 'w') as zipwrite:
            for filename in files_in_archive:
                zipwrite.write(filename)
        shutil.move(tempname, zipfname)
    finally:
        shutil.rmtree(tempdir)


def rewrite_tar(tarname: str):
    tempdir = tempfile.mkdtemp()
    compression = ""
    if tarname.endswith("gz"):
        compression = "gz"
    elif tarname.endswith("bz2"):
        compression = "bz2"
    try:
        ext = "" if len(compression) == 0 else "." + compression
        tempname = os.path.join(tempdir, 'new.tar' + ext)
        files_in_archive = [f for f in archives.keys() if archives[f] == tarname]
        with tarfile.open(tempname, 'w:' + compression) as tarwrite:
            for file in files_in_archive:
                tarwrite.add(file)
        shutil.move(tempname, tarname)
    finally:
        shutil.rmtree(tempdir)


def get_directory():
    directory = QFileDialog.getExistingDirectory(None, "Choose Directory", QDir.homePath(),
                                                 QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
    return directory
