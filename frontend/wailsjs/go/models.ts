export namespace audio {
	
	export class Device {
	    id: string;
	    name: string;
	    is_default: boolean;
	
	    static createFrom(source: any = {}) {
	        return new Device(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.id = source["id"];
	        this.name = source["name"];
	        this.is_default = source["is_default"];
	    }
	}

}

export namespace dict {
	
	export class Stats {
	    system_word_count: number;
	    user_word_count: number;
	    custom_word_count: number;
	    total_lookups: number;
	
	    static createFrom(source: any = {}) {
	        return new Stats(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.system_word_count = source["system_word_count"];
	        this.user_word_count = source["user_word_count"];
	        this.custom_word_count = source["custom_word_count"];
	        this.total_lookups = source["total_lookups"];
	    }
	}

}

export namespace pinyin {
	
	export class CandidateResult {
	    pinyin: string;
	    candidates: string[];
	    committed: string;
	    is_complete: boolean;
	
	    static createFrom(source: any = {}) {
	        return new CandidateResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.pinyin = source["pinyin"];
	        this.candidates = source["candidates"];
	        this.committed = source["committed"];
	        this.is_complete = source["is_complete"];
	    }
	}

}

