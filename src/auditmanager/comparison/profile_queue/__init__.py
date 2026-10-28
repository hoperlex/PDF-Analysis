"""The `page_profile` kind on the comparison queue (`CMP-PROFILE-QUEUE-01`, ADR-0025 decisions 4 and 6).

``handler.py`` is the one handler of the kind (it runs the builder of `CMP-PROFILE-01` for the item's
version and stops between pages on a cancel or a lost lease); ``enqueue.py`` is the call that puts a
version's profiles on the queue. Other contexts import both only through ``comparison/public.py``.
"""
