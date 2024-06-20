from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Date, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# Crea un motore che punta al file SQLite
engine = create_engine('sqlite:///psychology_study.db', echo=True)

# Crea una base dichiarativa
Base = declarative_base()

# Definisci i modelli di tabella
class Patient(Base):
    __tablename__ = 'patients'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    age = Column(Integer)
    gender = Column(String)
    diagnoses = relationship('Diagnosis', back_populates='patient')
    therapy_sessions = relationship('TherapySession', back_populates='patient')
    progress_reports = relationship('ProgressReport', back_populates='patient')

class Therapist(Base):
    __tablename__ = 'therapists'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    specialization = Column(String)
    therapy_sessions = relationship('TherapySession', back_populates='therapist')

class TherapySession(Base):
    __tablename__ = 'therapy_sessions'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    patient_id = Column(Integer, ForeignKey('patients.id'))
    therapist_id = Column(Integer, ForeignKey('therapists.id'))
    notes = Column(Text)
    patient = relationship('Patient', back_populates='therapy_sessions')
    therapist = relationship('Therapist', back_populates='therapy_sessions')

class Diagnosis(Base):
    __tablename__ = 'diagnoses'
    id = Column(Integer, primary_key=True)
    description = Column(Text, nullable=False)
    patient_id = Column(Integer, ForeignKey('patients.id'))
    patient = relationship('Patient', back_populates='diagnoses')
    treatments = relationship('Treatment', back_populates='diagnosis')

class Treatment(Base):
    __tablename__ = 'treatments'
    id = Column(Integer, primary_key=True)
    description = Column(Text, nullable=False)
    diagnosis_id = Column(Integer, ForeignKey('diagnoses.id'))
    medication_id = Column(Integer, ForeignKey('medications.id'))
    diagnosis = relationship('Diagnosis', back_populates='treatments')
    medication = relationship('Medication', back_populates='treatments')

class Medication(Base):
    __tablename__ = 'medications'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    dosage = Column(String)
    treatments = relationship('Treatment', back_populates='medication')

class ProgressReport(Base):
    __tablename__ = 'progress_reports'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    patient_id = Column(Integer, ForeignKey('patients.id'))
    report = Column(Text, nullable=False)
    patient = relationship('Patient', back_populates='progress_reports')

# Crea le tabelle
Base.metadata.create_all(engine)

# Crea una sessione
SessionMaker = sessionmaker(bind=engine)
session = SessionMaker()

# Esempio di popolamento delle tabelle
# Crea degli oggetti Patient
patient1 = Patient(name='Mario Rossi', age=35, gender='M')
patient2 = Patient(name='Luigi Bianchi', age=42, gender='M')
patient3 = Patient(name='Anna Verdi', age=28, gender='F')

# Crea degli oggetti Therapist
therapist1 = Therapist(name='Dott.ssa Silvia Neri', specialization='Psicoterapia Cognitivo-Comportamentale')
therapist2 = Therapist(name='Dott. Marco Gialli', specialization='Psicoterapia Psicodinamica')

# Aggiungi i pazienti e i terapisti alla sessione
session.add_all([patient1, patient2, patient3, therapist1, therapist2])
session.commit()

# Crea degli oggetti TherapySession
therapy_session1 = TherapySession(date=datetime.strptime('2023-01-10', '%Y-%m-%d').date(), patient=patient1, therapist=therapist1, notes='Prima seduta, valutazione iniziale.')
therapy_session2 = TherapySession(date=datetime.strptime('2023-01-15', '%Y-%m-%d').date(), patient=patient1, therapist=therapist1, notes='Discussione dei sintomi e pianificazione trattamento.')
therapy_session3 = TherapySession(date=datetime.strptime('2023-01-20', '%Y-%m-%d').date(), patient=patient2, therapist=therapist2, notes='Seduta di valutazione.')
therapy_session4 = TherapySession(date=datetime.strptime('2023-01-25', '%Y-%m-%d').date(), patient=patient3, therapist=therapist1, notes='Inizio terapia cognitivo-comportamentale.')

# Aggiungi le sedute alla sessione
session.add_all([therapy_session1, therapy_session2, therapy_session3, therapy_session4])
session.commit()

# Crea degli oggetti Diagnosis
diagnosis1 = Diagnosis(description='Disturbo d\'ansia generalizzato', patient=patient1)
diagnosis2 = Diagnosis(description='Depressione maggiore', patient=patient2)

# Aggiungi le diagnosi alla sessione
session.add_all([diagnosis1, diagnosis2])
session.commit()

# Crea degli oggetti Medication
medication1 = Medication(name='Sertralina', dosage='50mg')
medication2 = Medication(name='Escitalopram', dosage='10mg')

# Aggiungi i farmaci alla sessione
session.add_all([medication1, medication2])
session.commit()

# Crea degli oggetti Treatment
treatment1 = Treatment(description='Terapia Cognitivo-Comportamentale', diagnosis=diagnosis1, medication=medication1)
treatment2 = Treatment(description='Psicoterapia e farmacoterapia', diagnosis=diagnosis2, medication=medication2)

# Aggiungi i trattamenti alla sessione
session.add_all([treatment1, treatment2])
session.commit()

# Crea degli oggetti ProgressReport
progress_report1 = ProgressReport(date=datetime.strptime('2023-02-01', '%Y-%m-%d').date(), patient=patient1, report='Miglioramento dei sintomi di ansia.')
progress_report2 = ProgressReport(date=datetime.strptime('2023-02-05', '%Y-%m-%d').date(), patient=patient2, report='Lieve miglioramento dell\'umore.')

# Aggiungi i rapporti di progresso alla sessione
session.add_all([progress_report1, progress_report2])
session.commit()

# Esempio di query per ottenere i pazienti con le loro diagnosi
results = session.query(Patient, Diagnosis).join(Diagnosis).all()
for patient, diagnosis in results:
    print(patient.name, diagnosis.description)

# Esempio di query per ottenere i pazienti con le loro sedute
results = session.query(Patient, TherapySession).join(TherapySession).all()
for patient, therapy_session in results:
    print(patient.name, therapy_session.date, therapy_session.notes)
