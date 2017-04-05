isic.views.DatasetsView = isic.View.extend({
    // TODO refactor
    events: {
        'show.bs.collapse .isic-listing-panel-collapse': function (event) {
            var target = $(event.target);
            target.parent().find('.icon-right-open').removeClass('icon-right-open').addClass('icon-down-open');

            var viewIndex = parseInt(target.attr('data-model-index'), 10);
            var viewContainer = target.find('.isic-listing-panel-body');
            this.renderDataset(viewIndex, viewContainer);
        },
        'hide.bs.collapse .isic-listing-panel-collapse': function (event) {
            $(event.target).parent().find('.icon-down-open').removeClass('icon-down-open').addClass('icon-right-open');
        },
        'click .isic-dataset-add-button': function () {
            isic.router.navigate('dataset/create', {trigger: true});
        }
    },

    initialize: function (settings) {
        this.loaded = false;

        this.datasets = new isic.collections.DatasetCollection();
        this.listenTo(this.datasets, 'g:changed', function () {
            this.loaded = true;
            this.render();
        });
        this.datasets.fetch();

        this.paginateWidget = new girder.views.PaginateWidget({
            collection: this.datasets,
            parentView: this
        });

        this.render();
    },

    render: function () {
        this.$el.html(isic.templates.datasetsPage({
            title: 'Datasets',
            models: this.datasets.models,
            loaded: this.loaded,
            currentUser: girder.currentUser
        }));

        this.paginateWidget.setElement(this.$('.isic-listing-paginate-container')).render();

        // Display loading indicator
        if (!this.loaded) {
            this.loadingAnimation = new girder.views.LoadingAnimation({
                el: this.$('.isic-listing-loading-animation-container'),
                parentView: this
            }).render();
        } else {
            if (this.loadingAnimation) {
                this.loadingAnimation.destroy();
                delete this.loadingAnimation;
            }
        }

        return this;
    },

    renderDataset: function (index, container) {
        if (container.children().length === 0) {
            var dataset = this.datasets.at(index);

            new isic.views.DatasetView({ // eslint-disable-line no-new
                el: container,
                model: dataset,
                parentView: this
            });
        }
    }
});

isic.router.route('dataset', 'dataset', function () {
    var nextView = isic.views.DatasetsView;
    if (!isic.models.UserModel.currentUserCanAcceptTerms()) {
        nextView = isic.views.TermsAcceptanceView;
    }
    girder.events.trigger('g:navigateTo', nextView);
});