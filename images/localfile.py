"""Helper classes for dealing with local file operations."""


import os
import errno
import logging


################################################################################
# Standard File Copyer Class


class FileCopy(object):
    """
    File Copier for local file operations. Handles copying, linking and overwrite protection.

    Args:
        source_location (.location.LocationDescriptor): The `Location` to copy from.
            May be `None` if `source_path` is absolute.
        source_path (str): The relative path to copy from.
        dest_location (.location.LocationDescriptor): The `Location` to copy to. Required.
        dest_filename (str): The wanted filename to use on the destionation.
        link (Optional[boo]): Try hard-linking before copying. Defaults to `False`.
        keep_original (Optional[bool]): Keep source file, as opposed to deleting it when done.
            Defaults to whatever the source `Location.metadata.keep_original` is.
        dest_folder (str): Relative destination folder.
            If not given, let destionation `Location` decide.

    Attributes:
        destination_rel_path (str): After run, contains the relative path of the destination
            (from destination `Location` root).
        destination_full_path (str): After run, contains the full path of the destination.
        link (bool): Will be set to False if linking failed due to cross-device error.
    """
    def __init__(
            self,
            source_location=None,
            source_path=None,
            dest_location=None,
            dest_filename=None,
            link=False,
            keep_original=None,
            dest_folder=None):

        self.source_location = source_location
        if source_location and source_location.metadata and keep_original is None:
            self.keep_original = source_location.metadata.keep_original
        elif keep_original is None:
            self.keep_original = True
        else:
            self.keep_original = keep_original
        self.source_path = source_path
        self.dest_location = dest_location
        self.link = link
        self.dest_filename = dest_filename
        self.dest_folder = dest_folder
        self.destination_rel_path = None
        self.destination_full_path = None

    def run(self):
        if self.source_location:
            src = os.path.join(self.source_location.root, self.source_path)
        else:
            src = self.source_path
        dst_folder = self.dest_folder or self.dest_location.suggest_folder()
        dst = os.path.join(dst_folder, self.dest_filename)
        try:
            os.makedirs(dst_folder)
        except FileExistsError as e:
            pass
        c = 0
        while True:
            try:
                if c:
                    dst_path, dst_ext = os.path.splitext(dst)
                    fixed_dst = ''.join([dst_path, '_%i' % c, dst_ext])
                else:
                    fixed_dst = dst
                if self.link:
                    logging.debug("Linking %s -> %s", src, fixed_dst)
                    os.link(src, fixed_dst)
                    self.destination_rel_path = os.path.relpath(fixed_dst, self.dest_location.root)
                    self.destination_full_path = fixed_dst
                else:
                    import shutil
                    logging.debug("Copying %s -> %s", src, fixed_dst)
                    shutil.copyfile(src, fixed_dst)
                    self.destination_rel_path = os.path.relpath(fixed_dst, self.dest_location.root)
                    self.destination_full_path = fixed_dst
                break
            except FileExistsError:
                logging.warning("File exists %s", fixed_dst)
                c += 1
            except OSError as e:
                if e.errno == errno.EXDEV:
                    logging.warning("Cross-device link %s -> %s", src, fixed_dst)
                    self.link = False
                else:
                    logging.warning("OSError %i %s -> %s (%s)", e.errno, src, fixed_dst, str(e))
                    raise e

        if not self.keep_original:
            logging.debug("Removing original %s", src)
            os.remove(src)
