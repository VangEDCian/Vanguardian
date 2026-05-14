ALTER TABLE datacapture_fieldreview
DROP INDEX datacapture_fieldreview_page_field_type_uniq;

ALTER TABLE datacapture_fieldreview
ADD UNIQUE INDEX datacapture_fieldreview_page_field_type_uniq (
  page_state_id,
  field_template_id,
  review_type,
  data_version
);
