"use strict";

var DatasetForm = new function () {
    var obj = this;
    this.form_is_valid = true;

    this.validate_dataset = function () {
        $.getJSON(
            '/api/2/util/resource/validate_dataset',
            {
                'pkg_name': $('[name="pkg_name"]').val(),
                'owner_org': $('#field-organizations').val(),
                'unique_id': $('#field-unique_id').val(),
                'rights': $('#field-access-level-comment').val(),
                'license_url': $('#field-license-new').val(),
                'temporal': $('#field-temporal').val(),
                'described_by': $('#field-data_dictionary').val(),
                'described_by_type': $('#field-data_dictionary_type').val(),
                'conforms_to': $('#field-conforms_to').val(),
                'landing_page': $('#field-homepage_url').val(),
                'language': $('#field-language').val(),
                'investment_uii': $('#field-primary-it-investment-uii').val(),
                'references': $('#field-related_documents').val(),
                'issued': $('#field-release_date').val(),
                'system_of_records': $('#field-system_of_records').val()
            },
            function (result) {
                $('input').next('p.bad').remove();
                $('input').next('p.warning').remove();
                $('input').parent().prev('label').removeClass('bad');

                if (typeof(result.ResultSet['Warnings']) !== "undefined") {
                    var WarningObj = result.ResultSet['Warnings'];
                    for (var warningObjKey in WarningObj) {
                        if (WarningObj.hasOwnProperty(warningObjKey)) {
                            $('#field-' + warningObjKey).after('<p class="warning">Warning: '
                                + WarningObj[warningObjKey] + '</p>');
                        }
                    }
                }

                if (typeof(result.ResultSet['Invalid']) !== "undefined") {
                    var InvalidObj = result.ResultSet['Invalid'];
                    for (var invalidObjKey in InvalidObj) {
                        if (InvalidObj.hasOwnProperty(invalidObjKey)) {
                            $('#field-' + invalidObjKey).after('<p class="bad">'
                                + InvalidObj[invalidObjKey] + '</p>');
                            $('#field-' + invalidObjKey).parent().prev('label').addClass('bad');
                        }
                    }
                    obj.form_is_valid = false;
                } else {
                    obj.form_is_valid = true;
                }
            }
        );
    };

    this.bootstrap = function () {
        $("#field-is_parent").change(function () {
            if ('true' === $("#field-is_parent").val()) {
                $(".control-group-dataset-parent").hide();
                $("#field-parent_dataset").val("");
            } else {
                $(".control-group-dataset-parent").show();

            }
        }).change();

        $('#field-organizations')
            .add('#field-unique_id')
            .add('#field-access-level-comment')
            .add('#field-license-new')
            .add('#field-temporal')
            .add('#field-data_dictionary')
            .add('#field-data_dictionary_type')
            .add('#field-conforms_to')
            .add('#field-homepage_url')
            .add('#field-language')
            .add('#field-primary-it-investment-uii')
            .add('#field-related_documents')
            .add('#field-release_date')
            .add('#field-system_of_records')
            .change(this.validate_dataset);

        this.validate_dataset();

        $('form.dataset-form').submit(function (event) {
            if (!obj.form_is_valid) {
                event.preventDefault();
            }
        });

        $('#field-spatial').parents('div.control-group').addClass('exempt-allowed');
        $('#field-temporal').parents('div.control-group').addClass('exempt-allowed');
        $('#field-title').parents('div.control-group').addClass('exempt-allowed');
        $('#field-notes').parents('div.control-group').addClass('exempt-allowed');
        $('#field-modified').parents('div.control-group').addClass('exempt-allowed');
        $('#field-tags').parents('div.control-group').addClass('exempt-allowed');

        RedactionControl.append_redacted_icons();
        RedactionControl.preload_redacted_inputs();
        //$('.exemption_reason').renderEyes();
        this.reload_redacted_controls();
        $(':input[name="public_access_level"]').change(this.reload_redacted_controls);
    };

    this.reload_redacted_controls = function () {
        //  https://resources.data.gov/schemas/dcat-us/v1.1/#accessLevel
        var level = $(':input[name="public_access_level"]').val();
        if ('public' === level) {
            $('.redacted-icon').add('.redacted-marker').add('.exemption_reason').hide();
            return;
        }
        RedactionControl.show_redacted_controls();
    };
}();

$().ready(function () {
    if ($('form.dataset-form').length && $(':input[name="pkg_name"]').length) {
        DatasetForm.bootstrap();
    }
});

//$.fn.extend({
//    renderEyes: function () {
//        if ($(this).val()) {
//            $(this).parents('.control-group').children('.redacted-icon').removeClass('icon-eye-open');
//            $(this).parents('.control-group').children('.redacted-icon').addClass('icon-eye-close');
//        } else {
//            $(this).parents('.control-group').children('.redacted-icon').removeClass('icon-eye-close');
//            $(this).parents('.control-group').children('.redacted-icon').addClass('icon-eye-open');
//        }
//    }
//});


