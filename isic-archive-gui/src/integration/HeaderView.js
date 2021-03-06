import {getCurrentUser} from '@girder/core/auth';

import View from '../view';

import LayoutHeaderTemplate from './layoutHeader.pug';
import './layoutHeader.styl';

const LayoutHeaderView = View.extend({
    initialize: function (settings) {
        this.render();
    },

    render: function () {
        this.$el.html(LayoutHeaderTemplate({
            currentUser: getCurrentUser(),
            isicApiRoot: process.env.VUE_APP_ISIC_API_ROOT,
        }));

        return this;
    }
});

export default LayoutHeaderView;
