/*globals d3*/
isic.views.ImagesViewSubViews = isic.views.ImagesViewSubViews || {};

/*
var ICONS = {
    check: girder.staticRoot + '/built/plugins/isic_archive/extra/img/check.svg',
    ex: girder.staticRoot + '/built/plugins/isic_archive/extra/img/ex.svg',
    dash: girder.staticRoot + '/built/plugins/isic_archive/extra/img/dash.svg'
};
*/

isic.views.ImagesViewSubViews.IndividualHistogram = Backbone.View.extend({
    initialize: function (parameters) {
        this.attrName = parameters.attributeName;
        this.scale = new isic.views.ImagesViewSubViews
            .HistogramScale(this.attrName);
    },
    render: function () {
        var parentWidth = this.el.parentNode.getBoundingClientRect().width;
        var emSize = parseFloat(this.$el.css('font-size'));
        this.scale.update(this.model, emSize, parentWidth);

        var svg = d3.select(this.el);
        var width = this.scale.width;
        var topPadding = 0.5 * emSize;
        var height = this.scale.height + topPadding;

        if (!this.addedTemplate) {
            svg.html(isic.templates.imagesPageHistogram({
                staticRoot: girder.staticRoot
            }));
            this.addedTemplate = true;
        }

        // Draw the y axis
        var yScale = d3.scale.linear()
            .domain([0, this.scale.yMax])
            .range([height, topPadding]);
        var yAxis = d3.svg.axis()
            .scale(yScale)
            .orient('left')
            .ticks(Math.min(4, this.scale.yMax))
            .tickFormat(d3.format('s'));
        var yAxisObj = svg.select('.yAxis')
            .attr('transform', 'translate(' + this.scale.leftAxisPadding + ',0)')
            .call(yAxis);

        // Move the special buttons into place and attach their events
        this.$('.selectAllBins').hide();
        /*
        svg.select('.selectAllBins')
            .attr('transform', 'translate(' +
                (self.scale.leftAxisPadding - 0.5 * emSize) + ',' +
                (height + emSize) + ')');
        svg.select('.selectAll')
            .on('click', function () {
                self.model.clearFilters(self.attrName);
            });
        */

        // Draw the bin groups
        var labels = this.scale.overviewHistogram.map(function (d) {
            return d.label;
        });
        var bins = svg.select('.bins').selectAll('.bin')
            .data(labels, function (d) {
                return d;
            });
        var binsEnter = bins.enter().append('g')
            .attr('class', 'bin');
        bins.exit().remove();

        // Move the bins horizontally
        bins.attr('transform', _.bind(function (d) {
            var binNo = this.scale.labelToBin(d, 'overview');
            return 'translate(' + this.scale.binToPosition(binNo) + ',' + topPadding + ')';
        }, this));

        // Draw one bar for each bin
        binsEnter.append('rect')
            .attr('class', 'overview');
        binsEnter.append('rect')
            .attr('class', 'filteredSet');
        // Comment out this line to hide the page histogram (1/2):
        // binsEnter.append('rect')
        //     .attr('class', 'page');

        // Update each bar
        var drawBars = _.bind(function () {
            var self = this;
            bins.select('rect.overview')
                .each(function (d) {
                    // this refers to the DOM element
                    d3.select(this).attr(self.scale.getBinRect(d, 'overview'));
                });
            bins.select('rect.filteredSet')
                .each(function (d) {
                    // this refers to the DOM element
                    d3.select(this).attr(self.scale.getBinRect(d, 'filteredSet'));
                });
            // Comment out these lines to hide the page histogram (2/2):
            // bins.select('rect.page')
            //     .each(function (d) {
            //         // this refers to the DOM element
            //         d3.select(this).attr(self.scale.getBinRect(d, 'page'));
            //     });
        }, this);
        drawBars();

        // Add the scale adjustment knob (needs a distinct scale instance)
        var knobScale = yScale.copy();
        var knob = svg.select('.yAxisKnob')
            .attr('transform', 'translate(' +
                this.scale.leftAxisPadding + ',' +
                knobScale(this.scale.yMax) + ')');
        knob.call(d3.behavior.drag()
            .origin(function () {
                return { x: 0, y: knobScale(this.scale.yMax) };
            }).on('drag', function () {
                // the yMax setter automagically prevents bad values...
                this.scale.yMax = knobScale.invert(d3.event.y);

                // update everything that cares about the y this.scale:
                // the knob
                knob.attr('transform', 'translate(' +
                    this.scale.leftAxisPadding + ',' +
                    knobScale(this.scale.yMax) + ')');
                // the axis
                yScale.domain([0, this.scale.yMax]);
                yAxis.scale(yScale).ticks(Math.min(4, this.scale.yMax));
                yAxisObj.call(yAxis);
                // and the bars
                drawBars();
            }).on('dragstart', function () {
                svg.style('cursor', 'ns-resize');
            }).on('dragend', function () {
                svg.style('cursor', null);
            }));

        // Add an include / exclude button for each bin
        /*
        binsEnter.append('image')
            .attr('class', 'button')
            .attr({
                x: -0.5 * emSize,
                y: height + 0.5 * emSize,
                width: emSize,
                height: emSize
            });
        bins.select('image.button').each(function (d) {
            // this refers to the DOM element
            var bin = self.scale.labelToBin(d, 'overview');
            bin = self.model.get('overviewHistogram')[self.attrName][bin];
            var status = self.model.getBinStatus(self.attrName, bin);

            // To add / remove ranges, we might need to provide a comparison
            // function (undefined will just do default comparisons)
            var comparator;
            if (self.model.getAttributeType(self.attrName) === 'string') {
                comparator = function (a, b) {
                    return a.localeCompare(b);
                };
            }

            d3.select(this)
                .attr('xlink:href', function () {
                    if (status === window.ENUMS.BIN_STATES.INCLUDED) {
                        return ICONS.check;
                    } else if (status === window.ENUMS.BIN_STATES.EXCLUDED) {
                        return ICONS.ex;
                    } else {
                        return ICONS.dash;
                    }
                }).on('click', function (d) {
                    if (status === window.ENUMS.BIN_STATES.INCLUDED) {
                        // Remove this bin
                        if (bin.hasOwnProperty('lowBound') &&
                                bin.hasOwnProperty('highBound')) {
                            self.model.removeRange(self.attrName,
                                bin.lowBound, bin.highBound, comparator);
                        } else {
                            self.model.removeValue(self.attrName, bin.label);
                        }
                    } else {
                        // Add this bin
                        if (bin.hasOwnProperty('lowBound') &&
                                bin.hasOwnProperty('highBound')) {
                            self.model.includeRange(self.attrName,
                                bin.lowBound, bin.highBound, comparator);
                        } else {
                            self.model.includeValue(self.attrName, bin.label);
                        }
                    }
                });
        });
        height += 2 * emSize;
        */

        // Add each bin label, and compute the total needed height
        var offsetY = 0.25 * emSize;
        var transformHeight = height + offsetY;
        var transformAngle = -45;
        var transformAngleRadians = transformAngle * (Math.PI / 180);
        var maxBoxHeight = svg.select('.selectAllBins').select('text')
            .node().getComputedTextLength();
        binsEnter.append('text');
        bins.select('text')
            .text(function (d) {
                return d;
            })
            .attr('text-anchor', 'end')
            .attr('transform', 'translate(0 ' + transformHeight + ') rotate(' + transformAngle + ')')
            .each(function () {
                // this refers to the DOM element
                var boxHeight = Math.abs(this.getComputedTextLength() * Math.sin(transformAngleRadians));
                maxBoxHeight = Math.max(boxHeight, maxBoxHeight);
            });
        height += maxBoxHeight + topPadding + offsetY;

        svg.attr({
            width: width + 'px',
            height: height + 'px'
        });
        return this;
    }
});