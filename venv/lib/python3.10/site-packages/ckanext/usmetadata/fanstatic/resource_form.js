"use strict";

var DatasetResourceForm = new function () {
    var obj = this;

    this.form_is_valid = true;

    this.bootstrap = function () {
        $('input[name="resource_type"]').change(
            function () {
                obj.resource_type_change($(this).val());
            }
        );

        window.setInterval(function () {
            $('.resource-upload .btn').eq(2).remove();
            $('.resource-url .btn-remove-url').remove();
            obj.resource_type_change($('input[name="resource_type"]:checked').val());
        }, 500);


        $('#field-image-url').after('<p></p>');
        $('#field-image-url').add('#field-format').change(obj.verify_media_type);

        $('input[name="resource_type"]').change(obj.verify_media_type);

        if (document.URL.indexOf('/new_resource/') > 10) {
            obj.validate_resource();
        }

        $('input[name="resource_type"]').add('#field-format').add('#field-describedBy')
            .add('#field-describedByType').add('#field-conformsTo')
            .change(obj.validate_resource);

        $('form.dataset-resource-form').submit(function (event) {
            // allow submitting empty resource on dataset create
            if (!$('input[name="url"]').val() && $('#field-resource-type-file').prop("checked")) {
                $('#field-resource-type-file').prop("checked", false);
            }
            if (!obj.form_is_valid) {
                event.preventDefault();
            }
        });

        //  REDACTIONS
        $('#field-description').parents('div.control-group').addClass('exempt-allowed');

        //data.extras.filter(function( obj ) { return obj.key === 'public_access_level'; })[0].value

        try {
            var dataset_id = window.location.pathname.split('/')[2];
            if ('new_resource' === dataset_id) {
                dataset_id = window.location.pathname.split('/')[3];
            }
            var access_level = 'public';
            $.getJSON('/api/3/action/package_show?id=' + dataset_id).done(function (data) {
                access_level = data.result.extras.filter(function (obj) {
                    return obj.key === 'public_access_level';
                });
                if (!access_level.length) {
                    console.debug('public_access_level not found! invalid package!');
                } else {
                    access_level = access_level[0].value;
                }
                if ('public' !== access_level) {
                    //console.debug('nice');
                    RedactionControl.append_redacted_icons();
                    RedactionControl.preload_redacted_inputs();
                }
            });
        } catch (err) {
            //  sad
        }
    };

    this.validate_resource = function () {
        $.getJSON(
            '/api/2/util/resource/validate_resource',
            {
                'url': $('#field-image-url').val(),
                'resource_type': $('input[name="resource_type"]:checked').val(),
                'format': $('#field-format').val(),
                'describedBy': $('#field-describedBy').val(),
                'describedByType': $('#field-describedByType').val(),
                'conformsTo': $('#field-conformsTo').val()
            },
            function (result) {
                $('input').next('p.bad').remove();
                $('input').next('p.warning').remove();
                $('input').parent().prev('label').removeClass('bad');

                if (typeof(result.ResultSet['Warnings']) !== "undefined") {
                    var WarningObj = result.ResultSet['Warnings'];
                    for (var warningKey in WarningObj) {
                        if (WarningObj.hasOwnProperty(warningKey)) {
                            $('#field-' + warningKey).after('<p class="warning">Warning: ' + WarningObj[warningKey] + '</p>');
                        }
                    }
                }

                if (typeof(result.ResultSet['Invalid']) !== "undefined") {
                    var InvalidObj = result.ResultSet['Invalid'];
                    for (var invalidKey in InvalidObj) {
                        if (InvalidObj.hasOwnProperty(invalidKey)) {
                            $('#field-' + invalidKey).after('<p class="bad">' + InvalidObj[invalidKey] + '</p>');
                            $('#field-' + invalidKey).parent().prev('label').addClass('bad');
                        }
                    }
                    obj.form_is_valid = false;
                } else {
                    obj.form_is_valid = true;
                }
            }
        );
    };

    this.verify_media_type = function () {
        $('#field-image-url').next('p').replaceWith('<p></p>');

        var resource_type = $('input[name="resource_type"]:checked').val();
        var prepopulateMediaType = (resource_type === "file");
        if (resource_type === "upload" || resource_type === "api") {
            return
        }

        $('#field-image-url').next('p').replaceWith('<p>Detecting Media Type...</p>');
        $.getJSON(
            '/api/2/util/resource/content_type',
            {'url': $('#field-image-url').val()},
            function (result) {
                if (typeof(result.ResultSet['CType']) !== "undefined") {
                    var ct = result.ResultSet['CType'];
                    var status = result.ResultSet['Status'];
                    var reason = result.ResultSet['Reason'];
                    var sclass = (200 === status ? 'good' : 'bad');
                    var currentMediaType = $('#field-format').val();

                    var statusPrint = 'URL returned status <strong class="' + sclass + '">'
                        + status + ' (' + reason + ')</strong>';
                    var ctypePrint = '<br />Media Type was detected as <strong>' + ct + '</strong>';
                    var typeMatchPrint = '';

                    if (typeof(result.ResultSet['Redacted']) !== "undefined") {
                        typeMatchPrint = statusPrint = ctypePrint = '';
                    } else if (200 !== status) {
                        ctypePrint = '';
                    } else if ('' === currentMediaType) {
                        if (prepopulateMediaType) {
                            $('#field-format').val(ct);
                            $('#s2id_field-format').find('.select2-chosen').text(ct);
                            $('#s2id_field-format').find('.select2-choice').removeClass('select2-default');
                            typeMatchPrint = '<br /><span class="good">Detected type matches ' +
                                'currently selected type <strong>' + ct + '</strong></span>';
                        }
                    } else if (ct && ct.toLowerCase() === currentMediaType.toLowerCase()) {
                        if (prepopulateMediaType) {
                            typeMatchPrint = '<br /><span class="good">Detected type matches ' +
                                'currently selected type <strong>' + ct + '</strong></span>';
                        }
                    } else {
                        if (typeof(result.ResultSet['InvalidFormat']) !== "undefined") {
                            obj.form_is_valid = false;
                        }
                        if (prepopulateMediaType) {
                            typeMatchPrint = '<br /><span class="weird">Detected type <strong>' + ct + '</strong> ' +
                                'does not match currently selected type <strong>' + currentMediaType + '</strong></span>';
                        }
                    }

                    $('#field-image-url').next('p').replaceWith(
                        '<p>' + statusPrint + ctypePrint + typeMatchPrint + '</p>'
                    );
                } else {
                    var errorPrint = '';
                    var errorClass = 'weird';
                    if ("undefined" !== typeof(result.ResultSet['Error'])) {
                        errorPrint = result.ResultSet['Error'];
                    } else if ("undefined" !== typeof(result.ResultSet['ProtocolError'])) {
                        errorPrint = result.ResultSet['ProtocolError'];
                        errorClass = "weird";
                    }
                    if ("undefined" !== typeof(result.ResultSet['Red'])) {
                        errorClass = "red";
                    }
                    $('#field-image-url').next('p').replaceWith(
                        '<p class="' + errorClass + '">Could not reach given url: ' + errorPrint + '</p>'
                    );
                }
                obj.validate_resource();
            }
        );
    };

    this.resource_type_change = function (val) {
        if (!val) {
            return
        }
        $('.image-upload').show();
        $('#field-format').parents('.control-group').show();
        switch (val) {
            case 'upload':
                $('.resource-upload').show();
                if ($('input[name="url"]').val()) {
                    $('.resource-upload .btn').eq(1).show();
                }
                $('.resource-upload .btn').eq(0).show();
                $('#field-image-upload').show();
                $('.resource-url').hide();
                break;
            case 'api':
                if (!$('#field-format-readable').val()) {
                    $('#field-format-readable').val('API');
                }
                $('#field-format').parents('.control-group').hide();
                $('.resource-upload').hide();
                $('.resource-upload .btn').first().hide();
                $('.resource-url').show();
                break;
            default:
                $('.resource-upload').hide();
                $('.resource-upload .btn').first().hide();
                $('.resource-url').show();
        }
    };
}();

$().ready(function () {
    //to be sure we are editing a resource
    if ($('form.dataset-resource-form').length) {

        DatasetResourceForm.bootstrap();
    }
});
