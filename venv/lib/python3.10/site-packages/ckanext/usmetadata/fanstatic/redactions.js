"use strict";

//  https://resources.data.gov/schemas/dcat-us/v1.1/#accessLevel
var RedactionControl = new function () {
    var obj = this;

    // excluding these fields from partial redactions since they are not supported yet by POD schema v1.1
    this.excluded_partial_redactions = [
        'bureau_code',
        'category',
        'conformsTo',
        'conforms_to',
        'contact_email',
        'data_dictionary',
        'data_dictionary_type',
        'describedBy',
        'homepage_url',
        'language',
        'license_new',
        'modified',
        'primary_it_investment_uii',
        'program_code',
        'publisher',
        'related_documents',
        'release_date',
        'system_of_records',
        'tag_string',
        'temporal',
        'url'
    ];

    this.exempt_reasons = [
        {
            'value': 'B3',
            'short': 'B3 - Specifically exempted from disclosure by statute provided …',
            'full': "Specifically exempted from disclosure by statute (other than FOIA), provided that such " +
            "statute (A) requires that the matters be withheld from the public in such a manner as to leave no" +
            " discretion on the issue, or (B) establishes particular criteria for withholding or refers to" +
            " particular types of matters to be withheld."
        },
        {
            'value': 'B4',
            'short': 'B4 - Trade secrets and commercial or financial information obtained from …',
            'full': "Trade secrets and commercial or financial information obtained from a person" +
            " and privileged or confidential."
        },
        {
            'value': 'B5',
            'short': 'B5 - Inter-agency or intra-agency memorandums or letters which …',
            'full': "Inter-agency or intra-agency memorandums or letters which would not be available by law " +
            "to a party other than an agency in litigation with the agency."
        },
        {
            'value': 'B6',
            'short': 'B6 - Personnel and medical files and similar files the disclosure of which …',
            'full': "Personnel and medical files and similar files the disclosure of which would constitute" +
            " a clearly unwarranted invasion of personal privacy."
        }
    ];

    this.render_redacted_input = function (key, val) {
        val = typeof val !== 'undefined' ? val : false;

        var currentInput = $(':input[name="' + key + '"]');
        var controlsDiv = currentInput.parents('.controls');
        if (!controlsDiv.length) {
            return;
        }

        var reason_select = $(document.createElement('select'))
            .attr('name', "redacted_" + key)
            .attr('rel', key)
            .addClass('exemption_reason');


        $(document.createElement('option'))
            .attr('value', '')
            .text('Select FOIA Exemption Reason for Redaction')
            .appendTo(reason_select);

        for (var index in this.exempt_reasons) {
            var reason = this.exempt_reasons[index];
            var options = {
                value: reason.value, alt: reason.full, title: reason.full,
                text: reason.short
            };
            if (reason.value === val) {
                options['selected'] = 'selected';
            }
            $("<option />", options).appendTo(reason_select);
        }

        controlsDiv.append(reason_select);
        reason_select.change(toggle_redactions_buttons).trigger('change');
    };

    function toggle_redactions_buttons() {
        var input = $(this).parents('.control-group').find(':input[type=text],textarea');
        if (!input.length || input.length > 1) {
            return;
        }
        if ($.inArray(input.attr('name'), obj.excluded_partial_redactions) > -1) {
            return;
        }
        try {
            if (!$(this).val()) {
                $(this).parents('.control-group').find('.redacted-marker').hide();
                $(this).parents('.control-group').find('.redacted-clear').hide();
                return;
            }
        } catch (e) {
            return;
        }

        var redacted_reason = $(this).parents('.control-group').find('.exemption_reason');
        if (!$(this).parents('.control-group').find('.redacted-marker').length) {
            var partial_redactions_div = $(document.createElement('div'))
                .addClass('partial-redaction-buttons');
            var partial_marker = $(document.createElement('img'))
                .attr('src', '/partial_redaction.jpg')
                .addClass('redacted-marker')
                .attr('alt', "Select text and click the icon for partial redaction")
                .attr('title', "Select text and click the icon for partial redaction");

            var redaction_clear = $(document.createElement('img'))
                .attr('src', '/redaction_clear.png')
                .addClass('redacted-clear')
                .attr('alt', "Clear redactions")
                .attr('title', "Clear redactions");

            partial_redactions_div.append(partial_marker);
            partial_redactions_div.append(redaction_clear);

            partial_marker.click(apply_partial_redaction);
            redaction_clear.click(clear_partial_redaction);
            redacted_reason.after(partial_redactions_div);
            partial_redactions_div.toggle().toggle();
        } else {
            $(this).parents('.control-group').find('.redacted-marker').show();
            $(this).parents('.control-group').find('.redacted-clear').show();
        }
    }

    function apply_partial_redaction() {
        var input = $(this).parents('.control-group').find(':input[type=text],textarea');
        if (!input.length || input.length > 1) {
            return;
        }

        var reason = input.siblings('.exemption_reason').val();
        if (!reason) {
            return;
        }

        var start = 0, end = 0, normalizedValue, range,
            textInputRange, len, endRange;

        var el = input[0];

        if (typeof el.selectionStart === "number" && typeof el.selectionEnd === "number") {
            start = el.selectionStart;
            end = el.selectionEnd;
        } else {
            range = document.selection.createRange();

            if (range && range.parentElement() === el) {
                len = el.value.length;
                normalizedValue = el.value.replace(/\r\n/g, "\n");

                // Create a working TextRange that lives only in the input
                textInputRange = el.createTextRange();
                textInputRange.moveToBookmark(range.getBookmark());

                // Check if the start and end of the selection are at the very end
                // of the input, since moveStart/moveEnd doesn't return what we want
                // in those cases
                endRange = el.createTextRange();
                endRange.collapse(false);

                if (textInputRange.compareEndPoints("StartToEnd", endRange) > -1) {
                    start = end = len;
                } else {
                    start = -textInputRange.moveStart("character", -len);
                    start += normalizedValue.slice(0, start).split("\n").length - 1;

                    if (textInputRange.compareEndPoints("EndToEnd", endRange) > -1) {
                        end = len;
                    } else {
                        end = -textInputRange.moveEnd("character", -len);
                        end += normalizedValue.slice(0, end).split("\n").length - 1;
                    }
                }
            }
            document.selection.empty();
        }

        var selectionStart = start;
        var selectionEnd = end;

        if (!selectionEnd || selectionStart === selectionEnd) {
            return;
        }

        var redacted_text = input.val().substring(selectionStart, selectionEnd);
        var strLeft = input.val().substring(0, selectionStart);
        var strRight = input.val().substring(selectionEnd, input.val().length);
        redacted_text = '[[REDACTED-EX ' + reason + ']]' + redacted_text + '[[/REDACTED]]';
        input.val(strLeft + redacted_text + strRight);
    }

    function clear_partial_redaction() {
        var input = $(this).parents('.control-group').find(':input[type=text],textarea');
        if (!input.length || input.length > 1) {
            return;
        }

        var reason = input.siblings('.exemption_reason').val();
        if (!reason) {
            return;
        }

        var redacted_text = input.val();
        input.val(redacted_text.replace(/\[\[\/?REDACTED(-EX\sB\d)?\]\]/ig, ''));
    }

    this.redacted_icon_callback = function () {
        var controlsDiv = $(this).parent().find('.controls');
        if (controlsDiv.find('.exemption_reason').length) {
            if (!controlsDiv.find('.exemption_reason').val()) {
                controlsDiv.find('.exemption_reason').fadeToggle();
            }
            return;
        }
        var id = controlsDiv.find(':input[type=text],textarea,select').last().attr('name');
        obj.render_redacted_input(id);
    };

    this.preload_redacted_inputs = function () {
        var redacted;
        if ('undefined' !== typeof redacted_json_raw) {  //  dataset resource (or distribution) way
            redacted = redacted_json_raw;
        } else if ($('#redacted_json').size()) {     // dataset way
            var redactedJson = $('#redacted_json');
            redacted = $.parseJSON(redactedJson.val());
        }

        for (var field in redacted) {
            if (!redacted[field]) {
                continue;
            }
            obj.render_redacted_input(field.replace('redacted_', ''), redacted[field]);
        }
    };

    this.show_redacted_controls = function () {
        $('.redacted-icon').filter(function () {
            return !$(this).siblings('.redacted-marker:visible').length;
        }).show();
        $('.exemption_reason').filter(function () {
            return $(this).val() !== "";
        }).show();
    };

    this.append_redacted_icons = function () {
        var img = $('<img src="/redacted_icon.png" class="redacted-icon" alt="Mark as Redacted" title="Mark as Redacted">');
        $('.exempt-allowed .controls').before(img);

        $('.redacted-icon').click(obj.redacted_icon_callback);
        this.show_redaction_legend();
    };

    this.show_redaction_legend = function () {
        if (!$('.redactions-legend').length) {
            var legend_head = $(document.createElement('h3'))
                .text('Redaction Legend');
            var legend_text_1 = $(document.createElement('div'))
                .append($(document.createElement('img'))
                    .attr('src', '/redacted_icon.png')
                    .addClass('legend-redacted-icon')
            ).append(
                $(document.createElement('i'))
                    .text('- Redaction Icon')
            );
            var legend_text_2 = $(document.createElement('div'))
                .append($(document.createElement('img'))
                    .attr('src', '/partial_redaction.jpg')
                    .addClass('legend-redacted-icon')
            ).append(
                $(document.createElement('i'))
                    .text('- Partial Redaction Icon')
            );
            var legend_text_3 = $(document.createElement('div'))
                .append($(document.createElement('img'))
                    .attr('src', '/redaction_clear.png')
                    .addClass('legend-redacted-icon')
            ).append(
                $(document.createElement('i'))
                    .text('- Clear Redaction Icon')
            );

            var legend_link = $(document.createElement('a'))
                .attr('href', 'https://github.com/GSA/data.gov/wiki/Intentory.data.gov-User-Guide-for-Redaction-and-Partial-Redaction-Feature')
                .attr('target', '_blank')
                .text('read more')
                .addClass('redactions-legend-read-more');

            var redactions_legend = $(document.createElement('div'))
                .addClass('module-content redactions-legend')
                .append($(document.createElement('hr')))
                .append(legend_head)
                .append(legend_text_1)
                .append(legend_text_2)
                .append(legend_text_3)
                .append(legend_link);
            if ($('aside.secondary').length) {
                $('aside.secondary').append(redactions_legend);
            }
        }
    };
}();

$(document).ready(function () {
    if ($('.redacted-md').length) {
        $('.redacted-md')
            .each(function () {
                if ($(this).siblings('img.redacted-icon').length) {
                    $(this).html($(this).html().replace(/\~\~(.*?)\~\~/g, '<del>$1</del>'));
                } else {
                    $(this).html($(this).html().replace(/\~/g, ''));
                }
            })
    }
});



