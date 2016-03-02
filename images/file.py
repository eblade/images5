import os


# DB MODEL
##########

from enum import IntEnum
from sqlalchemy import Column, String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from samtt import Base
from .types import PropertySet, Property

class _File(Base):
    __tablename__ = 'file'
    __table_args__ = (
        UniqueConstraint('location_id', 'path', name='path_constraint'), 
    )

    class Purpose(IntEnum):
        source = 0
        primary = 1
        proxy = 2
        thumb = 3
        attachment = 4

    class ConflictException(Exception):
        pass

    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey('entry.id'))
    entry = relationship('_Entry')
    location_id = Column(Integer, ForeignKey('location.id'))
    location = relationship('_Location')
    path = Column(String(256), nullable=False)
    filesize = Column(Integer)
    purpose = Column(Integer, nullable=False, default=Purpose.primary)
    mime = Column(String(64))


# DESCRIPTOR
############

from enum import IntEnum
from .types import PropertySet, Property
from .location import Location


class File(PropertySet):
    id = Property(int)
    path = Property()
    location = Property(Location)
    entry_id = Property()
    filesize = Property(int, default=0)
    purpose = Property(enum=_File.Purpose, default=_File.Purpose.primary)
    mime = Property()

    @property
    def full_path(self):
        return os.path.join(self.location.root, self.path)

    @classmethod
    def map_in(self, file):
        f = File( 
            id=file.id,
            path=file.path,
            location=Location.map_in(file.location) if file.location else None,
            entry_id=file.entry_id,
            filesize=file.filesize,
            purpose=_File.Purpose(file.purpose),
            mime=file.mime
        )
        return f

    def map_out(self, f):
        f.path = self.path
        f.location_id = self.location.id if self.location else None
        f.entry_id = self.entry_id
        f.filesize = self.filesize
        f.purpose = self.purpose
        f.mime = self.mime


class FileFeed(PropertySet):
    count = Property(int)
    entries = Property(list)


# API
#####

from samtt import get_db
from sqlalchemy.exc import IntegrityError


def get_file_by_id(id):
    with get_db().transaction() as t:
        f = t.query(_File).get(id)
        return File.map_in(f)


def create_file(f):
    with get_db().transaction() as t:
        try:
            _f = _File()
            f.map_out(_f)
            t.add(_f)
            t.commit()
            id = _f.id
            return get_file_by_id(id)
        except IntegrityError as e:
            t.rollback()
    raise _File.ConflictException()


def update_file_by_id(id, f):
    with get_db().transaction() as t:
        _f = t.query(_File).get(id)
        f.map_out(_f)

    return get_file_by_id(id)


def delete_file_by_id(id):
    with get_db().transaction() as t:
        q = t.query(_File).filter(_File.id==id).delete()
