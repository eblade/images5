PROXY_SIZE = 1280
THUMB_SIZE = 200

#class ImportJob(Base):
#    __tablename__ = 'import_job'
#
#    class State(IntEnum):
#        new = 0
#        active = 1
#        done = 2 
#        failed = 3
#        hold = 4  # don't start yet
#        keep = 5  # don't clean this
#
#    class DefaultImportJobMetadata(PropertySet):
#        tags = Property(list)
#        metadata = Property() # just a string, don't open it
#        error = Property()
#        hidden = Property(bool, default=False)
#        access = Property(int, default=0)  # Private
#        delete_ts = Property()
#        source = Property()
#
#    id = Column(Integer, primary_key=True)
#    create_ts = Column(DateTime(timezone=True), default=func.now())
#    update_ts = Column(DateTime(timezone=True), onupdate=func.now())
#    path = Column(String(256), nullable=False)
#    state = Column(Integer, nullable=False, default=State.new)
#    data = Column(String(8192))
#    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
#    location_id = Column(Integer, ForeignKey('location.id'), nullable=False)
#    entry_id = Column(Integer, ForeignKey('entry.id'))
#
#    user = relationship(User)
#    location = relationship(Location)
#
#
#class ExportJob(Base):
#    __tablename__ = 'export_job'
#
#    class State(IntEnum):
#        new = 0
#        active = 1
#        done = 2 
#        failed = 3
#
#    class DefaultExportJobMetadata(PropertySet):
#        path = Property()
#        wants = Property(int)  # FileDescriptor.Purpose
#        longest_side = Property(int)
#
#    id = Column(Integer, primary_key=True)
#    create_ts = Column(DateTime(timezone=True), default=func.now())
#    update_ts = Column(DateTime(timezone=True), onupdate=func.now())
#    deliver_ts = Column(DateTime(timezone=True))
#    state = Column(Integer, nullable=False, default=State.new)
#    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
#    location_id = Column(Integer, ForeignKey('location.id'), nullable=False)
#    entry_id = Column(Integer, ForeignKey('entry.id'))
#    data = Column(String(8192))
#
#    location = relationship(Location)
#    entry = relationship('Entry')
#    user = relationship(User)
#
#
#
#
#register_metadata_schema(ImportJob.DefaultImportJobMetadata)
#register_metadata_schema(ExportJob.DefaultExportJobMetadata)
