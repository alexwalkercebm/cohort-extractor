"""
The ACME data is accessed via Presto which is a distributed query engine which
runs over multiple backing data stores ("connectors" in Presto's parlance).
The production configuration uses the following connectors:

    hive for views
    delta-lake for underlying data
    mysql for config/metadata

For immediate convenience while testing we use the SQL Server connector (as we
already need an instance running for the TPP tests).
"""
import os
import time

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Float, NVARCHAR, Date
from sqlalchemy import ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship

from datalab_cohorts.mssql_utils import mssql_sqlalchemy_engine_from_url
from datalab_cohorts.presto_utils import wait_for_presto_to_be_ready


Base = declarative_base()


def make_engine():
    engine = mssql_sqlalchemy_engine_from_url(
        os.environ["ACME_DATASOURCE_DATABASE_URL"]
    )
    timeout = os.environ.get("CONNECTION_RETRY_TIMEOUT")
    timeout = float(timeout) if timeout else 60
    # Wait for the database to be ready if it isn't already
    start = time.time()
    while True:
        try:
            engine.connect()
            break
        except sqlalchemy.exc.DBAPIError:
            if time.time() - start < timeout:
                time.sleep(1)
            else:
                raise
    wait_for_presto_to_be_ready(os.environ["ACME_DATABASE_URL"], timeout)
    return engine


def make_session():
    engine = make_engine()
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    return session


def make_database():
    Base.metadata.create_all(make_engine())


# WARNING: This table does not correspond to a table in the ACME database!
class MedicationIssue(Base):
    __tablename__ = "MedicationIssue"

    Patient_ID = Column(Integer, ForeignKey("Patient.Patient_ID"))
    Patient = relationship("Patient", back_populates="MedicationIssues")
    Consultation_ID = Column(Integer)
    MedicationIssue_ID = Column(Integer, primary_key=True)
    RepeatMedication_ID = Column(Integer)
    MultilexDrug_ID = Column(
        NVARCHAR(length=20), ForeignKey("MedicationDictionary.MultilexDrug_ID")
    )
    MedicationDictionary = relationship(
        "MedicationDictionary", back_populates="MedicationIssues", cascade="all, delete"
    )
    Dose = Column(String)
    Quantity = Column(String)
    StartDate = Column(DateTime)
    EndDate = Column(DateTime)
    MedicationStatus = Column(String)
    ConsultationDate = Column(DateTime)


# WARNING: This table does not correspond to a table in the ACME database!
class MedicationDictionary(Base):
    __tablename__ = "MedicationDictionary"

    MultilexDrug_ID = Column(NVARCHAR(length=20), primary_key=True)
    MedicationIssues = relationship(
        "MedicationIssue", back_populates="MedicationDictionary"
    )
    ProductId = Column(String)
    FullName = Column(String)
    RootName = Column(String)
    PackDescription = Column(String)
    Form = Column(String)
    Strength = Column(String)
    CompanyName = Column(String)
    DMD_ID = Column(String(collation="Latin1_General_CI_AS"))


# WARNING: This table does not correspond to a table in the ACME database!
class CodedEvent(Base):
    __tablename__ = "CodedEvent"

    Patient_ID = Column(Integer, ForeignKey("Patient.Patient_ID"))
    Patient = relationship(
        "Patient", back_populates="CodedEvents", cascade="all, delete"
    )
    CodedEvent_ID = Column(Integer, primary_key=True)
    CTV3Code = Column(String(collation="Latin1_General_BIN"))
    NumericValue = Column(Float)
    ConsultationDate = Column(DateTime)
    SnomedConceptId = Column(String)


# WARNING: This table does not correspond to a table in the ACME database!
class Patient(Base):
    __tablename__ = "Patient"

    Patient_ID = Column(Integer, primary_key=True)
    DateOfBirth = Column(Date)
    DateOfDeath = Column(Date)

    MedicationIssues = relationship(
        "MedicationIssue",
        back_populates="Patient",
        cascade="all, delete, delete-orphan",
    )
    CodedEvents = relationship(
        "CodedEvent", back_populates="Patient", cascade="all, delete, delete-orphan"
    )
    ICNARC = relationship(
        "ICNARC", back_populates="Patient", cascade="all, delete, delete-orphan"
    )
    ONSDeath = relationship(
        "ONSDeaths", back_populates="Patient", cascade="all, delete, delete-orphan"
    )
    CPNS = relationship(
        "CPNS", back_populates="Patient", cascade="all, delete, delete-orphan"
    )
    RegistrationHistory = relationship(
        "RegistrationHistory",
        back_populates="Patient",
        cascade="all, delete, delete-orphan",
    )
    Addresses = relationship(
        "PatientAddress", back_populates="Patient", cascade="all, delete, delete-orphan"
    )
    Sex = Column(String)


# WARNING: This table does not correspond to a table in the ACME database!
class RegistrationHistory(Base):
    __tablename__ = "RegistrationHistory"

    Registration_ID = Column(Integer, primary_key=True)
    Organisation_ID = Column(Integer, ForeignKey("Organisation.Organisation_ID"))
    Organisation = relationship(
        "Organisation", back_populates="RegistrationHistory", cascade="all, delete"
    )
    Patient_ID = Column(Integer, ForeignKey("Patient.Patient_ID"))
    Patient = relationship(
        "Patient", back_populates="RegistrationHistory", cascade="all, delete"
    )
    StartDate = Column(Date)
    EndDate = Column(Date)


# WARNING: This table does not correspond to a table in the ACME database!
class Organisation(Base):
    __tablename__ = "Organisation"

    Organisation_ID = Column(Integer, primary_key=True)
    GoLiveDate = Column(Date)
    STPCode = Column(String)
    MSOACode = Column(String)
    RegistrationHistory = relationship(
        "RegistrationHistory",
        back_populates="Organisation",
        cascade="all, delete, delete-orphan",
    )
    Region = Column(String)


# WARNING: This table does not correspond to a table in the ACME database!
class PatientAddress(Base):
    __tablename__ = "PatientAddress"

    PatientAddress_ID = Column(Integer, primary_key=True)
    Patient_ID = Column(Integer, ForeignKey("Patient.Patient_ID"))
    Patient = relationship("Patient", back_populates="Addresses", cascade="all, delete")
    StartDate = Column(Date)
    EndDate = Column(Date)
    AddressType = Column(Integer)
    RuralUrbanClassificationCode = Column(Integer)
    ImdRankRounded = Column(Integer)
    MSOACode = Column(String)


# WARNING: This table does not correspond to a table in the ACME database!
class ICNARC(Base):
    __tablename__ = "ICNARC"

    ICNARC_ID = Column(Integer, primary_key=True)
    Patient_ID = Column(Integer, ForeignKey("Patient.Patient_ID"))
    Patient = relationship("Patient", back_populates="ICNARC", cascade="all, delete")
    IcuAdmissionDateTime = Column(DateTime)
    OriginalIcuAdmissionDate = Column(Date)
    BasicDays_RespiratorySupport = Column(Integer)
    AdvancedDays_RespiratorySupport = Column(Integer)
    Ventilator = Column(Integer)


# WARNING: This table does not correspond to a table in the ACME database!
class ONSDeaths(Base):
    __tablename__ = "ONS_Deaths"

    # This column isn't in the actual database but SQLAlchemy gets a bit upset
    # if we don't give it a primary key
    id = Column(Integer, primary_key=True)
    Patient_ID = Column(Integer, ForeignKey("Patient.Patient_ID"))
    Patient = relationship("Patient", back_populates="ONSDeath", cascade="all, delete")
    Sex = Column(String)
    ageinyrs = Column(Integer)
    dod = Column(Date)
    icd10u = Column(String)
    ICD10001 = Column(String)
    ICD10002 = Column(String)
    ICD10003 = Column(String)
    ICD10004 = Column(String)
    ICD10005 = Column(String)
    ICD10006 = Column(String)
    ICD10007 = Column(String)
    ICD10008 = Column(String)
    ICD10009 = Column(String)
    ICD10010 = Column(String)
    ICD10011 = Column(String)
    ICD10012 = Column(String)
    ICD10013 = Column(String)
    ICD10014 = Column(String)
    ICD10015 = Column(String)


# WARNING: This table does not correspond to a table in the ACME database!
class CPNS(Base):
    __tablename__ = "CPNS"

    Patient_ID = Column(Integer, ForeignKey("Patient.Patient_ID"))
    Patient = relationship("Patient", back_populates="CPNS", cascade="all, delete")
    Id = Column(Integer, primary_key=True)
    # LocationOfDeath                                                 ITU
    # Sex                                                               M
    # DateOfAdmission                                          2020-04-02
    # DateOfSwabbed                                            2020-04-02
    # DateOfResult                                             2020-04-03
    # RelativesAware                                                    Y
    # TravelHistory                                                 False
    # RegionCode                                                      Y62
    # RegionName                                               North West
    # OrganisationCode                                                ABC
    # OrganisationName                                Test Hospital Trust
    # OrganisationTypeLot                                        Hospital
    # RegionApproved                                                 True
    # RegionalApprovedDate                                     2020-04-09
    # NationalApproved                                               True
    # NationalApprovedDate                                     2020-04-09
    # PreExistingCondition                                          False
    # Age                                                              57
    DateOfDeath = Column(Date)
    # snapDate                                                 2020-04-09
    # HadLearningDisability                                            NK
    # ReceivedTreatmentForMentalHealth                                 NK
    # Der_Ethnic_Category_Description                                None
    # Der_Latest_SUS_Attendance_Date_For_Ethnicity                   None
    # Der_Source_Dataset_For_Ethnicty                                None
