PYTHON ?= python

.PHONY: help install install-google run check smoke

help:
	@echo "Available targets:"
	@echo "  install         Install core dependencies"
	@echo "  install-google  Install core + Google dependencies"
	@echo "  run             Launch Task Logger GUI"
	@echo "  check           Run syntax checks"
	@echo "  smoke           Run backend local-only smoke test"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

install-google:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements-google.txt

run:
	$(PYTHON) taskLoggerGUI.py

check:
	$(PYTHON) -m py_compile taskLogger.py taskListGUI.py taskLoggerGUI.py

smoke:
	$(PYTHON) -c "import os,tempfile,taskLogger;fd,path=tempfile.mkstemp(suffix='.xlsx');os.close(fd);os.remove(path);r=taskLogger.add_task_to_log(task_name='smoke',start_date='2026-01-01',start_time='09:00',start_period='AM',end_date='2026-01-01',end_time='10:00',end_period='AM',timezone='UTC',task_log=path,attendees=['smoke@example.com'],sync_to_google=False);assert r['task_id'];u=taskLogger.update_task_in_log(task_id=r['task_id'],task_name='smoke2',start_date='2026-01-01',start_time='09:00',start_period='AM',end_date='2026-01-01',end_time='11:00',end_period='AM',timezone='UTC',task_log=path,attendees='smoke@example.com',sync_to_google=False);assert u['task_id']==r['task_id'];taskLogger.remove_task_from_log(task_id=r['task_id'],task_log=path,sync_to_google=False);d=taskLogger.load_task_log(path);assert len(d)==0;os.remove(path)"
