# Permission Gap Analysis

Nguon doi chieu:

- Runtime permission registry: `src/apps/identity/application/permissions.py`
- Runtime rename/alias map: `src/apps/identity/infrastructure/auth/authorization.py`
- Route permission hien tai: Django URL resolver va cac `permission_required` tren view/API

## Chuc nang thieu ro nhat

| Permission | Label | Ghi chu |
| --- | --- | --- |
| `DATA_EXPORT.RUN` | Run data export | Chua thay app/route export data. `src/apps/exporting` khong ton tai trong checkout hien tai. |
| `CASEBOOK.VIEW` | View casebook | Chua thay casebook UI/API. |
| `CASEBOOK.SIGN` | Sign casebook | Chua thay casebook signing UI/API; code hien moi co delegation policy nhac toi `CASEBOOK.SIGN`. |
| `DELEGATION.VIEW` | View delegation | Co model/policy delegation, nhung chua co man/API xem delegation. |
| `DELEGATION.MANAGE` | Manage delegation | Co model/policy delegation, nhung chua co man/API quan ly delegation. |
| `AE.VIEW` | View adverse events | Chua thay module/man adverse event. |
| `AE.ENTER` | Enter adverse events | Chua thay module/man adverse event. |
| `AE.MEDICAL_ASSESS` | Perform AE medical assessment | Chua thay module/man adverse event medical assessment. |
| `SAE.REPORT` | Report SAE | Chua thay module/man SAE reporting. |
| `DATA.FREEZE` | Freeze data | Co permission trong registry/default role, nhung chua thay action/route freeze. |
| `DATA.UNFREEZE` | Unfreeze data | Co permission trong registry/default role, nhung chua thay action/route unfreeze. |
| `DATA.UNLOCK` | Unlock data | Co permission trong registry/default role, nhung hien moi thay `DATA.LOCK` duoc dung cho lock page. |

## Co chuc nang gan dung nhung permission chua tach dung

| Permission | Label | Hien trang |
| --- | --- | --- |
| `AUDIT_TRAIL.VIEW` | View audit trail | Co subject/field audit history, nhung dang gate bang `subject.view_subject_detail`, chua dung `AUDIT_TRAIL.VIEW`. |
| `VALIDATION_ISSUE.VIEW` | View validation issues | Co validation issue trong Query Workbench, nhung view di qua `reconcile.view_dataquery`; chi `VALIDATION_ISSUE.ACKNOWLEDGE` duoc dung rieng. |
| `SDV.VIEW` | View SDV | Chua thay route/action rieng cho view SDV. |
| `SDV.MARK` | Mark SDV | Verify form da nen dung truc tiep `SDV.MARK`; can tranh giu lai check bang permission cu. |
| `SDR.MARK` | Mark SDR | Chua thay route/action rieng. |
| `EVENT_REVIEW.COMPLETE` | Complete event review | Chua thay route/action rieng. |
| `CRF.VIEW` | View CRF data | CRF enter/update/submit da co, nhung view CRF data chua dung permission rieng nay. |
| `CRF.REOPEN` | Reopen CRF data | Chua thay route/action reopen CRF data dung permission nay. |

## Permission app-level co ve du hoac chua wire

| Permission | Label | Hien trang |
| --- | --- | --- |
| `site.create_site_membership` | Can create site membership | Chi thay list/options API cho membership; chua co route tao membership rieng. |
| `site.update_site_membership` | Can update site membership | Chua thay route update membership rieng. |
| `site.delete_site_membership` | Can delete site membership | Chua thay route delete membership rieng. |
| `site.view_site_membership_detail` | Can view site membership detail | Chua thay route detail membership rieng. |
| `site.view_site_membership_history` | Can view site membership audit history | Chua thay route history membership rieng. |
| `subject.delete_subject` | Can delete subject | Co trong registry nhung chua thay delete subject route. |
| `study.assess_subject_eligibility` | Can assess subject eligibility | Co service/test lien quan eligibility, nhung UI route hien di qua workflow/update subject, chua gate bang permission nay. |
| `study.finalize_subject_eligibility` | Can finalize subject eligibility | Co service/test lien quan eligibility, nhung chua thay route gate bang permission nay. |
| `study.override_subject_eligibility` | Can override subject eligibility | Co trong registry, chua thay route gate bang permission nay. |
| `study.retract_subject_eligibility` | Can retract subject eligibility | Co service/test lien quan eligibility, nhung chua thay route gate bang permission nay. |
| `study.view_study_eventdefinition_list` | Can view study event definition list | Event definition list route dang dung `study.view_study_detail`. |
| `study.update_study_eventdefinition` | Can update study event definition | Co registry permission, nhung chua thay update route/action rieng. |
| `study.delete_study_eventdefinition` | Can delete study event definition | Co registry permission, nhung chua thay delete route/action rieng. |
| `study.view_study_history` | Can view study audit history | Co study audit service, nhung chua thay route gate bang permission nay. |

## Query permission note

Cac query action khong con thieu theo EDC permission moi:

- `QUERY.RESPOND`
- `QUERY.CLOSE`
- `QUERY.RETURN`
- `QUERY.CANCEL`

Code hien dung cac permission tren trong `QueryLifecycleActionAPIView` va `QueryWorkbenchView`.
Cac permission cu sau co ve la legacy/du:

- `reconcile.answer_dataquery`
- `reconcile.close_dataquery`
- `reconcile.reopen_dataquery`
- `reconcile.resolve_dataquery`

## Permission bi doi ten

Bang doi ten da duoc dung de migrate cac check runtime sang permission moi. Sau khi hoan tat migration, runtime khong nen tiep tuc phu thuoc vao alias map nua:

| Permission cu | Permission moi |
| --- | --- |
| `identity.view_user_list` | `USER_ACCESS.VIEW` |
| `identity.view_user_detail` | `USER_ACCESS.VIEW` |
| `identity.create_user` | `USER_ACCESS.MANAGE` |
| `identity.update_user` | `USER_ACCESS.MANAGE` |
| `identity.delete_user` | `USER_ACCESS.MANAGE` |
| `identity.restore_user` | `USER_ACCESS.MANAGE` |
| `study.view_study_list` | `STUDY_CONFIG.VIEW` |
| `study.view_study_detail` | `STUDY_CONFIG.VIEW` |
| `study.update_study` | `STUDY_CONFIG.MANAGE` |
| `study.manage_crf_template` | `STUDY_CONFIG.MANAGE` |
| `study.create_study_eventdefinition` | `STUDY_CONFIG.MANAGE` |
| `subject.view_subject_list` | `SUBJECT.VIEW` |
| `subject.view_subject_detail` | `SUBJECT.VIEW` |
| `subject.create_subject` | `SUBJECT.CREATE` |
| `subject.update_subject` | `SUBJECT.UPDATE` |
| `subject.verify_form` | `SDV.MARK` |

## Permission nen tiep tuc doi chieu

Cac permission duoi day co trong default roles, nhung scan code hien tai chua thay chuc nang tuong ung ro rang. Nen uu tien xac minh voi product scope truoc khi implement:

- `DATA_EXPORT.RUN`
- `CASEBOOK.VIEW`
- `CASEBOOK.SIGN`
- `DELEGATION.VIEW`
- `DELEGATION.MANAGE`
- `AE.VIEW`
- `AE.ENTER`
- `AE.MEDICAL_ASSESS`
- `SAE.REPORT`
- `DATA.FREEZE`
- `DATA.UNFREEZE`
- `DATA.UNLOCK`
- `CRF.REOPEN`
- `SDR.MARK`
- `EVENT_REVIEW.COMPLETE`
