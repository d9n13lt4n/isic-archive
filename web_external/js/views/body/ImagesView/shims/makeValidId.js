(function () {
    /* tool to make any string a valid DOM id (resolves regex collisions) */
    var ID_LOOKUP = {};
    var USED_IDS = {};

    isic.shims = isic.shims || {};
    isic.shims.makeValidId = function (str) {
        if (!ID_LOOKUP[str]) {
            var newID = str.replace(/^[^a-z]+|[^\w:.-]+/gi, '');
            var temp = newID;
            var i = 0;
            while (_.has(USED_IDS, temp)) {
                i += 1;
                temp = newID + i;
            }
            ID_LOOKUP[str] = temp;
            USED_IDS[temp] = true;
        }
        return ID_LOOKUP[str];
    };
})();