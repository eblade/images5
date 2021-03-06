import logging
import bottle
import datetime
import urllib

from sqlalchemy import Column, DateTime, String, Integer, Float, ForeignKey, func
from sqlalchemy.orm import relationship
from samtt import get_db, Base
from enum import IntEnum

from .file import File, _File
from .metadata import register_metadata_schema, wrap_raw_json
from .tag import Tag, _Tag, ensure_tag
from .types import PropertySet, Property
from .web import (
    Create,
    FetchById,
    FetchByQuery,
    UpdateById,
    DeleteById,
)
from .user import authenticate, no_guests, current_user_id, current_is_user


DELETE_AFTER = 24  # hours


# DB MODEL
##########


class _Entry(Base):
    __tablename__ = 'entry'

    class State(IntEnum):
        new = 0
        import_ready = 1
        importing = 2
        online = 3
        offline = 4
        import_failed = 5
        delete = 6
        deleted = 7

    class DefaultMetadata(PropertySet):
        title = Property()
        creator = Property()
        comment = Property()
        error = Property()

    class DefaultPhysicalMetadata(PropertySet):
        pass

    class Access(IntEnum):
        private = 0
        users = 1
        common = 2
        public = 3

    class Type(IntEnum):
        image = 0
        video = 1
        audio = 2
        other = 3

    id = Column(Integer, primary_key=True)
    original_filename = Column(String(256))
    source = Column(String(64))
    import_location_id = Column(Integer, ForeignKey('location.id'))
    type = Column(Integer, nullable=False, default=Type.image)
    state = Column(Integer, nullable=False, default=State.new)
    delete_ts = Column(DateTime(timezone=True))
    access = Column(Integer, nullable=False, default=Access.private)
    create_ts = Column(DateTime(timezone=True), default=func.now())
    update_ts = Column(DateTime(timezone=True), default=func.now(),
                       onupdate=func.now())
    taken_ts = Column(DateTime(timezone=True), default=func.now())
    latitude = Column(Float)
    longitude = Column(Float)

    data = Column(String(32768))
    physical_data = Column(String(32768))
    files = relationship('_File')
    tags = relationship('_Tag', secondary='entry_to_tag')

    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship('_User')
    parent_entry_id = Column(Integer, ForeignKey('entry.id'))
    parent_entry = relationship('_Entry')


register_metadata_schema(_Entry.DefaultMetadata)
register_metadata_schema(_Entry.DefaultPhysicalMetadata)


# WEB
#####


class App:
    BASE = '/entry'

    @classmethod
    def create(self):
        app = bottle.Bottle()
        app.add_hook('before_request', authenticate)

        app.route(
            path='/',
            callback=FetchByQuery(get_entries),
        )
        app.route(
            path='/<id:int>',
            callback=FetchById(get_entry_by_id),
        )
        app.route(
            path='/<id:int>',
            method='PUT',
            callback=UpdateById(update_entry_by_id, Entry),
            apply=no_guests,
        )
        app.route(
            path='/',
            method='POST',
            callback=Create(create_entry, Entry),
            apply=no_guests,
        )
        app.route(
            path='/<id:int>',
            method='DELETE',
            callback=DeleteById(delete_entry_by_id),
            apply=no_guests,
        )
        app.route(
            path='/source/<source>/<filename>',
            callback=lambda source, filename: get_entry_by_source(source, filename).to_json(),
            apply=no_guests,
        )

        return app


# DESCRIPTOR
############


class Entry(PropertySet):
    id = Property(int)
    path = Property()
    original_filename = Property()
    export_filename = Property()
    source = Property()
    import_location_id = Property(int)
    state = Property(enum=_Entry.State)
    delete_ts = Property()
    deleted = Property(bool, default=False)
    access = Property(enum=_Entry.Access, default=_Entry.Access.private)
    files = Property(list)
    tags = Property(list)

    create_ts = Property()
    update_ts = Property()
    taken_ts = Property()

    user_id = Property(int, default=1)
    parent_entry_id = Property()

    metadata = Property(wrap=True)
    physical_metadata = Property(wrap=True)

    primary_url = Property()
    proxy_url = Property()
    thumb_url = Property()

    self_url = Property()

    @property
    def latitude(self):
        if hasattr(self.physical_metadata, 'Latitude'):
            return self.physical_metadata.Latitude

    @property
    def longitude(self):
        if hasattr(self.physical_metadata, 'Longitude'):
            return self.physical_metadata.Longitude

    @property
    def tags_as_string(self):
        return ','.join(
            sorted([("~%s~" % tag.lower()) for tag in self.tags if tag])
        )

    @property
    def source_file(self):
        try:
            return [file for file in self.files if file.purpose == _File.Purpose.source][0]
        except IndexError:
            return None

    def calculate_urls(self):
        self.self_url = '%s/%i' % (App.BASE, self.id)
        # for fd in self.files:
        #     if fd.purpose == FileDescriptor.Purpose.primary:
        #         self.primary_url = api.url().location.get_download_url(fd.location_id, fd.path)
        #     if fd.purpose == FileDescriptor.Purpose.proxy:
        #         self.proxy_url = api.url().location.get_download_url(fd.location_id, fd.path)
        #     if fd.purpose == FileDescriptor.Purpose.thumb:
        #         self.thumb_url = api.url().location.get_download_url(fd.location_id, fd.path)

    @classmethod
    def map_in(self, entry):
        ed = Entry(
            id=entry.id,
            user_id=entry.user_id,
            state=_Entry.State(entry.state),
            access=_Entry.Access(entry.access),
            original_filename=entry.original_filename,
            source=entry.source,
            import_location_id=entry.import_location_id,
            create_ts=entry.create_ts.strftime('%Y-%m-%d %H:%M:%S'),
            update_ts=entry.update_ts.strftime('%Y-%m-%d %H:%M:%S') if entry.update_ts else None,
            taken_ts=entry.taken_ts.strftime('%Y-%m-%d %H:%M:%S') if entry.taken_ts else None,
            delete_ts=entry.delete_ts.strftime('%Y-%m-%d %H:%M:%S') if entry.delete_ts else None,
            deleted=entry.delete_ts is not None,
            files=[File.map_in(f) for f in entry.files] if entry.files else [],
            tags=sorted([Tag.map_in(t) for t in entry.tags]) if entry.tags else [],
            metadata=wrap_raw_json(entry.data),
            physical_metadata=wrap_raw_json(entry.physical_data),
        )
        # ed.calculate_urls()
        return ed

    def map_out(self, entry, system=False):
        entry.original_filename = self.original_filename
        entry.export_filename = self.export_filename
        entry.source = self.source
        entry.import_location_id = self.import_location_id
        entry.state = self.state
        entry.taken_ts = (datetime.datetime.strptime(
            self.taken_ts, '%Y-%m-%d %H:%M:%S').replace(microsecond=0)
            if self.taken_ts else None
        )
        if self.deleted and self.delete_ts is None:
            self.delete_ts = ((
                datetime.datetime.utcnow() + datetime.timedelta(hours=DELETE_AFTER)
            ).strftime('%Y-%m-%d %H:%M:%S'))
        elif self.deleted is False and self.delete_ts is not None:
            self.delete_ts = None
        entry.delete_ts = (datetime.datetime.strptime(
            self.delete_ts, '%Y-%m-%d %H:%M:%S').replace(microsecond=0)
            if self.delete_ts else None
        )
        entry.access = self.access
        entry.data = self.metadata.to_json() if self.metadata else None
        entry.physical_data = (
            self.physical_metadata.to_json() if self.physical_metadata else None
        )
        entry.user_id = self.user_id
        entry.parent_entry_id = self.parent_entry_id
        entry.latitude = self.latitude
        entry.longitude = self.longitude
        with get_db().transaction() as t:
            entry.tags = [t.query(_Tag).get(tag.id) for tag in self.tags]
            entry.files = [t.query(_File).get(file.id) for file in self.files]


class EntryFeed(PropertySet):
    count = Property(int)
    total_count = Property(int)
    prev_link = Property()
    next_link = Property()
    offset = Property(int)
    entries = Property(list)


class EntryQuery(PropertySet):
    start_ts = Property(none='')
    end_ts = Property(none='')
    image = Property(bool, default=True)
    video = Property(bool, default=False)
    audio = Property(bool, default=False)
    other = Property(bool, default=False)
    show_deleted = Property(bool, default=False)
    only_deleted = Property(bool, default=False)
    include_tags = Property(list)
    exclude_tags = Property(list)
    source = Property()

    next_ts = Property(none='')
    prev_offset = Property(int)
    page_size = Property(int, default=25, required=True)
    order = Property(default='desc', required=True)

    @classmethod
    def FromQuery(self):
        eq = EntryQuery()

        eq.start_ts = bottle.request.query.start_ts
        eq.end_ts = bottle.request.query.end_ts

        eq.next_ts = bottle.request.query.next_ts
        if bottle.request.query.prev_offset not in (None, ''):
            eq.prev_offset = bottle.request.query.prev_offset
        if bottle.request.query.page_size not in (None, ''):
            eq.page_size = bottle.request.query.page_size
        if bottle.request.query.order not in (None, ''):
            eq.order = bottle.request.query.order

        eq.image = bottle.request.query.image == 'yes'
        eq.video = bottle.request.query.video == 'yes'
        eq.audio = bottle.request.query.audio == 'yes'
        eq.other = bottle.request.query.other == 'yes'

        eq.source = bottle.request.query.source

        eq.show_deleted = bottle.request.query.show_deleted == 'yes'
        eq.only_deleted = bottle.request.query.only_deleted == 'yes'

        decoded = bottle.request.query.decode()
        eq.include_tags = decoded.getall('include_tags')
        eq.exclude_tags = decoded.getall('exclude_tags')
        return eq

    def to_query_string(self):
        return urllib.parse.urlencode(
            (
                ('start_ts', self.start_ts),
                ('end_ts', self.end_ts),
                ('next_ts', self.next_ts),
                ('prev_offset', self.prev_offset or ''),
                ('page_size', self.page_size),
                ('order', self.order),
                ('image', 'yes' if self.image else 'no'),
                ('video', 'yes' if self.video else 'no'),
                ('audio', 'yes' if self.audio else 'no'),
                ('other', 'yes' if self.other else 'no'),
                ('source', self.source),
                ('show_deleted', 'yes' if self.show_deleted else 'no'),
                ('only_deleted', 'yes' if self.only_deleted else 'no'),
            ) +
            tuple([
                ('include_tags', tag) for tag in self.include_tags
            ]) +
            tuple([
                ('exclude_tags', tag) for tag in self.exclude_tags
            ])
        )


#####
# API


def get_entries(query=None, system=False):
    with get_db().transaction() as t:
        q = (
            t.query(_Entry).order_by(_Entry.taken_ts.desc(), _Entry.create_ts.desc())
        )
        if not system:
            q = q.filter(
                (_Entry.user_id == current_user_id()) | (_Entry.access >= _Entry.Access.users)
            )

            if not current_is_user():
                q = q.filter(_Entry.access >= _Entry.Access.public)

        if query is not None:
            logging.info("Query: %s", query.to_json())

            if query.start_ts:
                start_ts = (datetime.datetime.strptime(
                    query.start_ts, '%Y-%m-%d')
                    .replace(hour=0, minute=0, second=0, microsecond=0))
                q = q.filter(_Entry.taken_ts >= start_ts)

            if query.end_ts:
                end_ts = (datetime.datetime.strptime(
                    query.end_ts, '%Y-%m-%d')
                    .replace(hour=0, minute=0, second=0, microsecond=0))
                q = q.filter(_Entry.taken_ts < end_ts)

            types = [t.value for t in _Entry.Type if getattr(query, t.name)]
            if types:
                q = q.filter(_Entry.type.in_(types))

            if not query.show_deleted:
                q = q.filter(_Entry.delete_ts.is_(None))
            if query.only_deleted:
                q = q.filter(_Entry.delete_ts.isnot(None))

            for tag in query.include_tags:
                q = q.filter(_Entry.tags.like('%~' + tag + '~%'))
            for tag in query.exclude_tags:
                q = q.filter(~_Entry.tags.like('%~' + tag + '~%'))

            if query.source:
                q = q.filter(_Entry.source == query.source)

        total_count = q.count()

        # Default values for when no paging occurs
        offset = 0
        total_count_paged = total_count

        # Paging
        if query is not None:
            if query.next_ts:
                end_ts = (datetime.datetime.strptime(
                    query.next_ts, '%Y-%m-%d %H:%M:%S').replace(microsecond=0))
                q = q.filter(_Entry.taken_ts < end_ts)
                total_count_paged = q.count()
                offset = total_count - total_count_paged

            elif query.prev_offset:
                q = q.offset(query.prev_offset)
                total_count_paged = total_count
                offset = query.prev_offset

            logging.info(q)
            page_size = query.page_size
            entries = q.limit(page_size).all()

        else:
            entries = q.all()

        count = len(entries)

        result = EntryFeed(
            count=count,
            total_count=total_count,
            offset=offset,
            entries=[Entry.map_in(entry) for entry in entries],
        )

        # Paging
        if query is not None:
            if total_count > count:
                query.next_ts = result.entries[-1].taken_ts
                result.next_link = App.BASE + '?' + query.to_query_string()

            if count > 0 and offset > 0:
                query.next_ts = ''
                query.prev_offset = max(offset - page_size, 0)
                result.prev_link = App.BASE + '?' + query.to_query_string()

        return result


def get_entry_by_id(id):
    with get_db().transaction() as t:
        entry = t.query(_Entry).filter(_Entry.id == id).one()
        return Entry.map_in(entry)


def get_entry_by_source(source, filename, system=False):
    with get_db().transaction() as t:
        q = t.query(_Entry).filter(
            _Entry.source == source,
            _Entry.original_filename == filename
        )
        if not system:
            q = q.filter(
                (_Entry.user_id == current_user_id()) | (_Entry.access >= _Entry.Access.public)
            )
        entry = q.one()
        return Entry.map_in(entry)


def update_entry_by_id(id, ed, system=False):
    with get_db().transaction() as t:
        q = t.query(_Entry).filter(_Entry.id == id)
        if not system:
            q = q.filter(
                (_Entry.user_id == current_user_id()) | (_Entry.access >= _Entry.Access.common)
            )
        entry = q.one()
        ed.map_out(entry)

    return get_entry_by_id(id)


def create_entry(ed, system=False):
    with get_db().transaction() as t:
        entry = _Entry()

        for tag in ed.tags:
            ensure_tag(tag)

        ed.map_out(entry, system=system)
        t.add(entry)
        t.commit()
        id = entry.id

    return get_entry_by_id(id)


def delete_entry_by_id(id, system=False):
    with get_db().transaction() as t:
        q = t.query(_Entry).filter(_Entry.id == id)
        if not system:
            q = q.filter(
                (_Entry.user_id == current_user_id()) | (_Entry.access >= _Entry.Access.common)
            )
        q.delete()
