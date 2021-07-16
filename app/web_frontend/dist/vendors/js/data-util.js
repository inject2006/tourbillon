'use strict';

function DataUtil() {}

function getInputValue(formId) {
  var inputs = $("#" + formId).find('input');
  var form_data = {};
  inputs.toArray().forEach(function (elm) {
    if (elm.type === 'checkbox' || elm.type === 'radio') {
      form_data[elm.name] = elm.checked;
    } else if ($(elm).data("type") === "date") {
      form_data[elm.name] = new Date(elm.value).getTime();
    } else {
      form_data[elm.name] = elm.value;
    }
  });
  return form_data;
}

function getTextareaValue(formId) {
  var inputs = $("#" + formId).find('textarea');
  var form_data = {};
  inputs.toArray().forEach(function (elm) {
      form_data[elm.name] = elm.value;
  });
  return form_data;
}

function getSelectValue(formId) {
  var selections = $("#" + formId).find('select');
  var select_data = {};
  selections.toArray().forEach(function (elm) {
    select_data[elm.name] = elm.value;
  });
  return select_data;
}

DataUtil.prototype.getFormData = function (formId) {
  var inputsValue = getInputValue(formId);
  var selectionsValue = getSelectValue(formId);
  var textareaValue = getTextareaValue(formId);
  var formData = Object.assign({}, inputsValue, selectionsValue,textareaValue);
  return formData;
};

window.DataUtil = new DataUtil();